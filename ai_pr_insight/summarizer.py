import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple
import logging
from dataclasses import dataclass
import numpy as np
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm
from dotenv import load_dotenv
import argparse
import re
import time

@dataclass
class SummaryConfig:
    """Configuration for summary generation"""
    similarity_threshold: float = 0.90
    batch_size: int = 50
    model_name: str = "text-embedding-3-small"
    abstraction_threshold: float = 0.85  # Threshold for grouping similar items for abstraction

class PRAnalysisSummarizer:
    def __init__(self, config: SummaryConfig):
        """Initialize the summarizer with OpenAI client and configuration."""
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.config = config
        self.item_embeddings = []
        self.items_text = []
        self.categories: Set[str] = set()
        
        # Enhanced logging setup
        logging.basicConfig(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('summary.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_embedding(self, text: str, retry_count=3) -> np.ndarray:
        """Get embedding for a text using OpenAI's embedding model with retries."""
        for attempt in range(retry_count):
            try:
                response = self.client.embeddings.create(
                    model=self.config.model_name,
                    input=text
                )
                return np.array(response.data[0].embedding)
            except Exception as e:
                if attempt == retry_count - 1:
                    self.logger.error(f"Final error getting embedding: {e}")
                    return None
                self.logger.warning(f"Embedding attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(1)  # Wait before retry

    def load_json_files(self, directory: Path) -> List[Dict]:
        """Recursively load all JSON files from the given directory."""
        items = []
        json_files = list(directory.rglob("*.json"))
        
        self.logger.info(f"Found {len(json_files)} JSON files to process")
        
        with tqdm(total=len(json_files), desc="Loading JSON files") as pbar:
            for file_path in json_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        if isinstance(data, dict) and "items_by_category" in data:
                            for category, descriptions in data["items_by_category"].items():
                                self.categories.add(category)
                                items.extend([
                                    {"category": category, "description": desc}
                                    for desc in descriptions
                                ])
                        elif isinstance(data, list):
                            items.extend(data)
                            for item in data:
                                if "category" in item:
                                    self.categories.add(item["category"])
                        
                        self.logger.debug(f"Processed {file_path.name}: {len(items)} total items")
                        
                except Exception as e:
                    self.logger.error(f"Error loading {file_path}: {e}")
                finally:
                    pbar.update(1)
        
        return items

    def is_semantically_duplicate(self, item: Dict[str, str]) -> bool:
        """Check if an item is semantically similar to existing items."""
        full_text = f"{item['category']} {item['description']}"
        new_embedding = self.get_embedding(full_text)
        
        if new_embedding is None:
            return False
            
        if self.item_embeddings:
            existing_embeddings = np.array(self.item_embeddings)
            similarities = cosine_similarity([new_embedding], existing_embeddings)[0]
            
            if np.any(similarities > self.config.similarity_threshold):
                most_similar_idx = np.argmax(similarities)
                self.logger.debug(
                    f"Duplicate found:\nNew: {full_text}\n"
                    f"Existing: {self.items_text[most_similar_idx]}\n"
                    f"Similarity: {similarities[most_similar_idx]:.3f}"
                )
                return True
                
        self.item_embeddings.append(new_embedding)
        self.items_text.append(full_text)
        return False

    def process_items_in_batches(self, items: List[Dict]) -> List[Dict]:
        """Process items in batches to avoid rate limits."""
        unique_items = []
        total_batches = (len(items) + self.config.batch_size - 1) // self.config.batch_size
        
        with tqdm(total=len(items), desc="Processing items") as pbar:
            for i in range(0, len(items), self.config.batch_size):
                batch = items[i:i + self.config.batch_size]
                for item in batch:
                    if not self.is_semantically_duplicate(item):
                        unique_items.append(item)
                    pbar.update(1)
        
        return unique_items

    def abstract_rule(self, descriptions: List[str], retry_count=3) -> Tuple[str, List[str]]:
        """Generate an abstract rule from specific descriptions using GPT with retries."""
        prompt = (
            "Below are several specific code review checklist items. "
            "Please create:\n1. A single abstract/generic rule that captures "
            "the common principle\n2. Keep the original items as examples\n\n"
            "Specific items:\n" + "\n".join(f"- {d}" for d in descriptions)
        )

        for attempt in range(retry_count):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": (
                            "You are a technical documentation expert. When given specific "
                            "code review checklist items, create a general rule that captures "
                            "their essence. Respond in this format only:\n"
                            "RULE: <the general rule>\n"
                            "EXAMPLES: <comma-separated list of specific examples>"
                        )},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )

                response_text = response.choices[0].message.content
                rule_match = re.search(r"RULE: (.*?)(?:\nEXAMPLES:|$)", response_text, re.DOTALL)
                examples_match = re.search(r"EXAMPLES: (.*?)$", response_text, re.DOTALL)
                
                rule = rule_match.group(1).strip() if rule_match else descriptions[0]
                examples = examples_match.group(1).strip().split(", ") if examples_match else descriptions[1:]
                
                return rule, examples

            except Exception as e:
                if attempt == retry_count - 1:
                    self.logger.error(f"Final error in abstract_rule: {e}")
                    return descriptions[0], descriptions[1:]
                self.logger.warning(f"Abstract rule attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(1)

    def find_similar_groups(self, items: List[Dict]) -> List[List[Dict]]:
        """Find groups of similar items for abstraction with progress tracking."""
        if not items:
            return []

        self.logger.info("Generating embeddings for similarity grouping...")
        embeddings = []
        with tqdm(total=len(items), desc="Generating embeddings") as pbar:
            for item in items:
                embedding = self.get_embedding(f"{item['category']} {item['description']}")
                if embedding is not None:
                    embeddings.append(embedding)
                pbar.update(1)

        embeddings = np.array(embeddings)
        self.logger.info("Computing similarity matrix...")
        similarity_matrix = cosine_similarity(embeddings)
        
        processed = set()
        groups = []
        
        self.logger.info("Finding similar groups...")
        with tqdm(total=len(items), desc="Finding groups") as pbar:
            for i in range(len(items)):
                if i in processed:
                    pbar.update(1)
                    continue

                similar_indices = np.where(similarity_matrix[i] > self.config.abstraction_threshold)[0]
                if len(similar_indices) > 2:
                    group = [items[idx] for idx in similar_indices]
                    groups.append(group)
                    processed.update(similar_indices)
                pbar.update(1)

        self.logger.info(f"Found {len(groups)} groups of similar items")
        return groups

    def abstract_similar_items(self, items: List[Dict]) -> List[Dict]:
        """Find similar items and abstract them into general rules with examples."""
        self.logger.info("Starting abstraction process...")
        similar_groups = self.find_similar_groups(items)
        result_items = []
        
        processed_items = set()
        if similar_groups:
            self.logger.info("Abstracting similar groups...")
            with tqdm(total=len(similar_groups), desc="Abstracting groups") as pbar:
                for group in similar_groups:
                    descriptions = [item['description'] for item in group]
                    category = group[0]['category']
                    
                    general_rule, examples = self.abstract_rule(descriptions)
                    
                    result_items.append({
                        'category': category,
                        'description': general_rule,
                        'examples': examples
                    })
                    
                    processed_items.update(item['description'] for item in group)
                    pbar.update(1)

        # Add remaining items
        remaining_items = [item for item in items if item['description'] not in processed_items]
        self.logger.info(f"Adding {len(remaining_items)} remaining items")
        result_items.extend(remaining_items)
        
        return result_items

    def summarize(self, input_dir: str, output_dir: str):
        """Main method to process all JSON files and generate consolidated output."""
        try:
            self.logger.info("Starting summarization process...")
            input_path = Path(input_dir)
            output_path = Path(output_dir)
            
            self.logger.info("Loading JSON files...")
            all_items = self.load_json_files(input_path)
            self.logger.info(f"Loaded {len(all_items)} total items")
            
            self.logger.info("Processing items to find unique entries...")
            unique_items = self.process_items_in_batches(all_items)
            self.logger.info(f"Found {len(unique_items)} unique items")
            
            self.logger.info("Abstracting similar items...")
            abstracted_items = self.abstract_similar_items(unique_items)
            self.logger.info(f"Generated {len(abstracted_items)} abstracted items")
            
            self.logger.info("Saving results...")
            self.save_results(abstracted_items, output_path)
            self.logger.info("Summarization complete!")
            
        except Exception as e:
            self.logger.error(f"Error during summarization: {e}")
            raise

    def save_results(self, items: List[Dict], output_dir: Path) -> None:
        """Save consolidated results in both JSON and Markdown formats."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir.mkdir(exist_ok=True)
            
            # Prepare output structure
            output = {
                "generated_at": timestamp,
                "total_items": len(items),
                "items_by_category": {}
            }
            
            # Group items by category
            for item in items:
                cat = item['category']
                if cat not in output["items_by_category"]:
                    output["items_by_category"][cat] = []
                
                # Handle items with examples
                if 'examples' in item:
                    entry = {
                        'rule': item['description'],
                        'examples': item['examples']
                    }
                else:
                    entry = item['description']
                    
                output["items_by_category"][cat].append(entry)
            
            # Save JSON output
            json_path = output_dir / f"consolidated_analysis_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            
            # Save Markdown checklist
            md_path = output_dir / f"consolidated_checklist_{timestamp}.md"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write("# Consolidated PR Review Checklist\n\n")
                f.write(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for category in sorted(output["items_by_category"].keys()):
                    f.write(f"\n## {category}\n\n")
                    for item in output["items_by_category"][category]:
                        if isinstance(item, dict):  # Item with examples
                            f.write(f"- [ ] {item['rule']}\n")
                            f.write("  Examples:\n")
                            for example in item['examples']:
                                f.write(f"    - {example}\n")
                        else:  # Simple item
                            f.write(f"- [ ] {item}\n")
            
            self.logger.info(f"Results saved to:\n- {json_path}\n- {md_path}")
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")

def main():
    parser = argparse.ArgumentParser(description='Consolidate multiple PR analysis results')
    parser.add_argument('input_dir', help='Directory containing JSON analysis files')
    parser.add_argument('output_dir', help='Directory to save consolidated results')
    parser.add_argument('--similarity-threshold', type=float, default=0.90,
                       help='Threshold for considering items similar (0.0 to 1.0)')
    parser.add_argument('--abstraction-threshold', type=float, default=0.85,
                       help='Threshold for grouping items for abstraction (0.0 to 1.0)')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Number of items to process in each batch')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    config = SummaryConfig(
        similarity_threshold=args.similarity_threshold,
        batch_size=args.batch_size,
        abstraction_threshold=args.abstraction_threshold
    )
    
    summarizer = PRAnalysisSummarizer(config)
    summarizer.summarize(args.input_dir, args.output_dir)

if __name__ == "__main__":
    main()
