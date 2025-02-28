import argparse
import sys
import logging
from pkg_resources import get_distribution
from ai_pr_insight.fetcher import GitHubPRCommentsFetcher
from ai_pr_insight.analyzer import PRCommentsAnalyzer
from ai_pr_insight.config import Config
from ai_pr_insight.utils import setup_logging
from ai_pr_insight.summarizer import PRAnalysisSummarizer, SummaryConfig
from ai_pr_insight.diagnostic import GitHubAPIDiagnostic

def main():
    parser = argparse.ArgumentParser(description="AI PR Insight - Analyze PR comments and generate insights.")
    parser.add_argument('--verbose', action='store_true', help="Enable verbose logging (debug mode)")
    parser.add_argument('--version', action='version', version=f'%(prog)s {get_distribution("ai-pr-insight").version}')
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Fetch subcommand
    fetch_parser = subparsers.add_parser('fetch', help="Fetch PR comments from GitHub")
    fetch_parser.add_argument('--year', type=int, required=True, help="Year to filter comments")
    fetch_parser.add_argument('--month', type=int, required=True, help="Month to filter comments")
    fetch_parser.add_argument('--org', type=str, help="GitHub organization to filter repositories")
    fetch_parser.add_argument('--username', type=str, help="GitHub username to filter PRs")
    fetch_parser.add_argument('--output_file', type=str, default="pr-comments.json", help="Output file path")
    fetch_parser.set_defaults(func=fetch_pr_comments_wrapper)

    # Analyze subcommand
    analyze_parser = subparsers.add_parser('analyze', help="Analyze PR comments and generate checklist")
    analyze_parser.add_argument('--input_file', type=str, required=True, help="Input JSON file with PR comments")
    analyze_parser.add_argument('--output_dir', type=str, default="checklist.md", help="Output checklist file")
    analyze_parser.add_argument('--batch-size', type=int, default=10, help="Number of comments to process in each batch")
    analyze_parser.add_argument('--model-tier', choices=['economy', 'premium'], default='economy', help="Model tier (economy: GPT-3.5, premium: GPT-4)")
    analyze_parser.set_defaults(func=analyze_pr_comments_wrapper)

    # Summarize subcommand
    summarize_parser = subparsers.add_parser('summarize', help="Consolidate and summarize PR analysis results")
    summarize_parser.add_argument('--input_dir', help="Directory containing JSON analysis files")
    summarize_parser.add_argument('--output_dir', help="Directory to save consolidated results")
    summarize_parser.add_argument('--similarity-threshold', type=float, default=0.90,
                                  help="Threshold for considering items similar (0.0 to 1.0)")
    summarize_parser.add_argument('--abstraction-threshold', type=float, default=0.85,
                                  help="Threshold for grouping items for abstraction (0.0 to 1.0)")
    summarize_parser.add_argument('--batch-size', type=int, default=50,
                                  help="Number of items to process in each batch")
    summarize_parser.add_argument('--debug', action='store_true', help="Enable debug logging")
    summarize_parser.set_defaults(func=summarize_pr_analysis_wrapper)

    # Diagnose subcommand
    diagnose_parser = subparsers.add_parser('diagnose', help="Run diagnostics to test GitHub API access and authentication")
    diagnose_parser.set_defaults(func=diagnose_github_api_wrapper)

    args = parser.parse_args()

    # Set up logging
    logger = setup_logging()  # Get the logger instance
    if args.verbose:
        logger.setLevel(logging.DEBUG)  # Set logging level to DEBUG if verbose mode is enabled
        logger.debug("Debug mode enabled")

    try:
        # Call the appropriate function based on the subcommand
        if args.command == "fetch":
            # Fetch PR comments
            comments = args.func(args)  # Pass the args object to the wrapper function
            
            # Save the comments to the output file
            import json
            with open(args.output_file, 'w') as f:  # Use args.output_file instead of args.output
                json.dump(comments, f, indent=2)
            logger.info(f"Saved {len(comments)} comments to {args.output_file}")
        
        elif args.command == "analyze":
            # Analyze PR comments
            args.func(args)
            logger.info(f"Checklist generated at {args.output_dir}")
        
        elif args.command == "summarize":
            # Summarize PR analysis results
            args.func(args)
            logger.info(f"Summarization complete! Results saved to {args.output_dir}")
        
        elif args.command == "diagnose":
            # Run GitHub API diagnostics
            args.func(args)
            logger.info("Diagnostics completed.")
    
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

def fetch_pr_comments_wrapper(args):
    """Wrapper function to handle the fetch subcommand."""
    fetcher = GitHubPRCommentsFetcher(
        token=Config().github_token,  # Get the token from the Config class
        year=args.year,
        month=args.month,
        target_username=args.username,
        target_org=args.org
    )
    return fetcher.fetch_all_pr_comments()

def analyze_pr_comments_wrapper(args):
    """Wrapper function to handle the analyze subcommand."""
    analyzer = PRCommentsAnalyzer(batch_size=args.batch_size, model_tier=args.model_tier)

    analyzer.analyze_comments(args.input_file, args.output_dir)

def summarize_pr_analysis_wrapper(args):
    """Wrapper function to handle the summarize subcommand."""
    config = SummaryConfig(
        similarity_threshold=args.similarity_threshold,
        batch_size=args.batch_size,
        abstraction_threshold=args.abstraction_threshold
    )
    
    summarizer = PRAnalysisSummarizer(config)
    summarizer.summarize(args.input_dir, args.output_dir)

def diagnose_github_api_wrapper(args):
    """Wrapper function to handle the diagnose subcommand."""
    diagnostic = GitHubAPIDiagnostic()
    diagnostic.debug_github_api()

if __name__ == "__main__":
    main()
