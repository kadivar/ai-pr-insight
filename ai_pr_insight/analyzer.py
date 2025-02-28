import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple
import time
from dotenv import load_dotenv
from openai import OpenAI
import argparse
import re
from tiktoken import encoding_for_model
from tqdm import tqdm
import time
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

@dataclass
class ModelConfig:
    """Configuration for different OpenAI models"""
    name: str
    max_tokens: int
    cost_per_1k_tokens: float
    daily_token_limit: int
    request_limit: int

class ModelTier(Enum):
    ECONOMY = [
        ModelConfig("gpt-3.5-turbo", 4000, 0.0015, 200_000, 200),  # Basic tier
        ModelConfig("gpt-3.5-turbo-16k", 16000, 0.003, 200_000, 200)  # For larger batches
    ]
    PREMIUM = [
        ModelConfig("gpt-4", 8000, 0.03, 100_000, 100),  # More accurate but expensive
        ModelConfig("gpt-4-turbo-preview", 128000, 0.01, 100_000, 100)  # Best for large batches
    ]

class PRCommentsAnalyzer:
    def __init__(self, batch_size: int = 10, model_tier: str = "economy", similarity_threshold: float = 0.90):
        """Initialize the analyzer with OpenAI client and configuration."""
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.batch_size = batch_size
        self.seen_items = set()
        
        # Setup logging
        logging.basicConfig(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('analysis.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize model configuration
        self.model_tier = ModelTier[model_tier.upper()]
        self.current_model_index = 0
        self.current_model = self.model_tier.value[0]
        
        # Initialize quota tracking
        self.reset_quota_tracking()

        self.item_embeddings = []  # Store embeddings
        self.items_text = []       # Store corresponding text
        self.similarity_threshold = similarity_threshold

    def debug_print(self, message: str) -> None:
        """Log debug messages if DEBUG is enabled."""
        if os.getenv('LOG_LEVEL', 'INFO') == 'DEBUG':
            self.logger.debug(message)

    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for a text using OpenAI's embedding model."""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            self.logger.error(f"Error getting embedding: {e}")
            return None

    def check_quota_reset(self):
        """Check if daily quota should be reset"""
        if datetime.now() - self.last_reset > timedelta(days=1):
            self.reset_quota_tracking()

    def switch_model(self) -> bool:
        """Try to switch to next available model in tier"""
        self.current_model_index += 1
        if self.current_model_index < len(self.model_tier.value):
            self.current_model = self.model_tier.value[self.current_model_index]
            self.logger.info(f"Switched to model: {self.current_model.name}")
            return True
        return False

    def reset_quota_tracking(self):
        """Reset daily quota tracking"""
        self.daily_tokens = 0
        self.daily_requests = 0
        self.last_reset = datetime.now()

    def estimate_tokens(self, text: str) -> int:
        """Estimate the token usage for a given text."""
        try:
            encoder = encoding_for_model(self.current_model.name)
            return len(encoder.encode(text))
        except Exception as e:
            self.logger.warning(f"Error estimating tokens: {e}")
            # Fallback to rough estimation
            return len(text.split()) * 1.3
        
    def load_comments(self, file_path: str) -> List[Dict]:
        """Load comments from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                comments = json.load(f)
                self.logger.info(f"Loaded {len(comments)} comments")
                return comments
        except Exception as e:
            self.logger.error(f"Error loading comments: {e}")
            return []  # Return an empty list to avoid crashes
            
    def prepare_batches(self, comments: List[Dict]) -> List[List[Dict]]:
        """Intelligently split comments into batches based on token limits."""
        batches = []
        current_batch = []
        current_tokens = 0
        
        for comment in comments:
            comment_text = self.create_prompt([comment])
            comment_tokens = self.estimate_tokens(comment_text)
            
            # If adding this comment would exceed token limit
            if current_tokens + comment_tokens > self.current_model.max_tokens * 0.8:  # 20% safety margin
                if current_batch:  # If we have a partial batch
                    batches.append(current_batch)
                    current_batch = []
                    current_tokens = 0
                
                # If single comment is too large for current model
                if comment_tokens > self.current_model.max_tokens * 0.8:
                    if self.switch_model():  # Try switching to a model with larger context
                        current_batch = [comment]
                        current_tokens = comment_tokens
                    else:
                        self.logger.warning(f"Comment too large for any available model, skipping: {comment['pr_number']}")
                        continue
                else:
                    current_batch = [comment]
                    current_tokens = comment_tokens
            else:
                current_batch.append(comment)
                current_tokens += comment_tokens
                    
        if current_batch:
            batches.append(current_batch)
                
        return batches
    
    def create_prompt(self, batch: List[Dict]) -> str:
        """Create a prompt for ChatGPT from a batch of comments."""
        comments_text = "\n\n".join([
            f"Comment {i+1}:\n"
            f"Author: {comment['author']}\n"
            f"Context: PR #{comment['pr_number']} - {comment['pr_title']}\n"
            f"Message: {comment['message']}\n"
            f"Source code (if any): {comment['source_code']}"
            for i, comment in enumerate(batch)
        ])
        
        return f"""Analyze these PR comments and extract key points that should be checked before publishing a PR. 
        Focus on common issues, best practices, and recurring themes.
        Format each point in exactly this format with no variations:
        [Category] Item description
        
        Categories should be one of:
        - Code Quality
        - Documentation
        - Testing
        - Performance
        - Security
        - Maintainability
        - Version Control
        - Code Style
        
        Comments to analyze:
        {comments_text}
        """
    
    def normalize_item(self, item: str) -> str:
        """Normalize a checklist item to help with deduplication."""
        # Remove leading/trailing whitespace and convert to lowercase
        item = item.strip().lower()
        # Remove punctuation and extra spaces
        item = re.sub(r'[^\w\s]', '', item)
        item = re.sub(r'\s+', ' ', item)
        return item

    def is_semantically_duplicate(self, item: Dict[str, str]) -> bool:
        """Check if an item is semantically similar to existing items."""
        # Combine category and description for semantic comparison
        full_text = f"{item['category']} {item['description']}"
        
        # Get embedding for new item
        new_embedding = self.get_embedding(full_text)
        if new_embedding is None:
            return False  # If we can't get embedding, assume it's not a duplicate
            
        # If we have existing items, check similarity
        if self.item_embeddings:
            # Convert list to numpy array for efficient computation
            existing_embeddings = np.array(self.item_embeddings)
            
            # Calculate similarities with all existing items
            similarities = cosine_similarity([new_embedding], existing_embeddings)[0]
            
            # Check if any similarity exceeds threshold
            if np.any(similarities > self.similarity_threshold):
                most_similar_idx = np.argmax(similarities)
                self.logger.debug(f"Duplicate found:\nNew: {full_text}\nExisting: {self.items_text[most_similar_idx]}\nSimilarity: {similarities[most_similar_idx]:.3f}")
                return True
                
        # If not duplicate, store embedding and text
        self.item_embeddings.append(new_embedding)
        self.items_text.append(full_text)
        return False

    def get_chatgpt_analysis(self, prompt: str) -> Tuple[str, int]:
        """Get analysis from ChatGPT with quota management."""
        self.check_quota_reset()
        
        # Check if we've hit quota limits
        if (self.daily_tokens >= self.current_model.daily_token_limit or 
            self.daily_requests >= self.current_model.request_limit):
            
            if not self.switch_model():
                raise RuntimeError("Daily quota exceeded for all available models")
                
        try:
            response = self.client.chat.completions.create(
                model=self.current_model.name,
                messages=[
                    {"role": "system", "content": """You are a specialized code review assistant. 
                    For each point you identify:
                    1. Be specific and actionable
                    2. Focus on concrete checks rather than general advice
                    3. Use consistent category labels
                    4. Format exactly as: [Category] Item description"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            
            content = response.choices[0].message.content
            total_tokens = response.usage.total_tokens
            
            # Update quota tracking
            self.daily_tokens += total_tokens
            self.daily_requests += 1
            
            return content, total_tokens
            
        except Exception as e:
            if "insufficient_quota" in str(e).lower():
                if self.switch_model():
                    # Retry with new model
                    return self.get_chatgpt_analysis(prompt)
                else:
                    raise RuntimeError("Quota exceeded for all available models")
            else:
                self.logger.error(f"Error in ChatGPT analysis: {e}")
                return "", 0

    def parse_checklist_items(self, text: str) -> List[Dict[str, str]]:
        """Parse checklist items from text into structured format."""
        items = []
        for line in text.split('\n'):
            line = line.strip()
            if line and '[' in line and ']' in line:
                try:
                    category = re.search(r'\[(.*?)\]', line).group(1)
                    description = line.split(']', 1)[1].strip()
                    items.append({
                        'category': category,
                        'description': description
                    })
                except:
                    continue
        return items


    def analyze_comments(self, file_path: str, output_dir: str = "output") -> None:
        """Main analysis method with enhanced error handling and progress tracking."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)  # Ensure the output directory exists
        
        # Load and prepare data
        comments = self.load_comments(file_path)  # Directly load the list of comments
        self.logger.info(f"Number of comments: {len(comments)}")
        
        batches = self.prepare_batches(comments)
        
        # Initialize progress tracking
        total_batches = len(batches)
        all_items = []
        last_save_time = datetime.now()
        save_interval = timedelta(minutes=5)  # Save progress every 5 minutes
        
        with tqdm(total=total_batches, desc="Processing batches", unit="batch") as pbar:
            for i, batch in enumerate(batches):
                try:
                    prompt = self.create_prompt(batch)
                    analysis, tokens_used = self.get_chatgpt_analysis(prompt)
                    
                    if analysis:
                        items = self.parse_checklist_items(analysis)
                        for item in items:
                            if not self.is_semantically_duplicate(item):
                                all_items.append(item)
                                self.logger.debug(f"New unique item: [{item['category']}] {item['description']}")
                    
                    # Update progress
                    pbar.update(1)
                    pbar.set_postfix({
                        "Model": self.current_model.name,
                        "Tokens": self.daily_tokens,
                        "Requests": self.daily_requests
                    })
                    
                    # Save progress periodically
                    if datetime.now() - last_save_time > save_interval:
                        self.save_progress(all_items, output_path)  # Save progress to the output directory
                        last_save_time = datetime.now()
                    
                    # Rate limiting
                    time.sleep(20 if "gpt-4" in self.current_model.name else 5)
                    
                except RuntimeError as e:
                    self.logger.error(f"Critical error: {e}")
                    self.save_progress(all_items, output_path)
                    break
                except Exception as e:
                    self.logger.error(f"Error processing batch {i+1}: {e}")
                    continue
        
        # Save final results
        self.save_final_results(all_items, output_path)

    def save_progress(self, items: List[Dict], output_dir: Path) -> None:
        """Save intermediate results to a JSON file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            progress_file = output_dir / f"progress_{timestamp}.json"
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Progress saved to: {progress_file}")
        except Exception as e:
            self.logger.error(f"Error saving progress: {e}")

    def save_final_results(self, items: List[Dict[str, str]], output_dir: Path):
        """Save final results with similarity groups."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create detailed output with similarity information
        output = {
            "generated_at": timestamp,
            "total_items": len(items),
            "items_by_category": {},
            "similarity_groups": []
        }
        
        # Group items by category
        for item in items:
            cat = item['category']
            if cat not in output["items_by_category"]:
                output["items_by_category"][cat] = []
            output["items_by_category"][cat].append(item['description'])
        
        # Generate similarity matrix for all items
        all_embeddings = np.array(self.item_embeddings)
        similarity_matrix = cosine_similarity(all_embeddings)
        
        # Find groups of similar items
        processed_indices = set()
        for i in range(len(items)):
            if i in processed_indices:
                continue
                
            # Find all items similar to this one
            similar_indices = np.where(similarity_matrix[i] > self.similarity_threshold)[0]
            if len(similar_indices) > 1:  # If there are similar items
                group = {
                    "primary_item": f"[{items[i]['category']}] {items[i]['description']}",
                    "similar_items": [
                        {
                            "item": f"[{items[j]['category']}] {items[j]['description']}",
                            "similarity": float(similarity_matrix[i][j])
                        }
                        for j in similar_indices if j != i
                    ]
                }
                output["similarity_groups"].append(group)
                processed_indices.update(similar_indices)
        
        # Save detailed JSON output
        json_path = output_dir / f"analysis_detailed_{timestamp}.json"  # Save JSON file in the output directory
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        # Save markdown checklist
        md_path = output_dir / "checklist.md"  # Save Markdown file in the output directory
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# PR Review Checklist\n\n")
            f.write(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for category, items in output["items_by_category"].items():
                f.write(f"\n## {category}\n\n")
                for item in items:
                    f.write(f"- [ ] {item}\n")
                    
            # Add similarity information at the end
            if output["similarity_groups"]:
                f.write("\n## Note on Similar Items\n\n")
                f.write("The following items were identified as potentially similar:\n\n")
                for group in output["similarity_groups"]:
                    f.write(f"* {group['primary_item']}\n")
                    for similar in group['similar_items']:
                        f.write(f"  - {similar['item']} (similarity: {similar['similarity']:.2f})\n")
        self.logger.info(f"Final results saved to:\n- {json_path}\n- {md_path}")

def main():
    parser = argparse.ArgumentParser(description='Analyze PR comments using ChatGPT')
    parser.add_argument('file_path', help='Path to the JSON file containing PR comments')
    parser.add_argument('--batch-size', type=int, default=10, 
                       help='Number of comments to process in each batch')
    parser.add_argument('--output-dir', default='output',
                       help='Directory to save output files')
    parser.add_argument('--model-tier', choices=['economy', 'premium'], default='economy',
                       help='Choose model tier (economy: GPT-3.5, premium: GPT-4)')
    
    args = parser.parse_args()
    
    analyzer = PRCommentsAnalyzer(batch_size=args.batch_size, model_tier=args.model_tier)
    analyzer.analyze_comments(args.file_path, args.output_dir)

if __name__ == "__main__":
    main()
