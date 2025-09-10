"""
Main entry point for the Event Poster Analyzer.

Usage:
    python main.py --image path/to/poster.jpg --api-key YOUR_CLAUDE_API_KEY
    python main.py --batch path/to/images/ --api-key YOUR_CLAUDE_API_KEY --output results/
"""

import asyncio
import argparse
import logging
import json
import os
import sys
from pathlib import Path
from typing import List

# Add the poster_analyzer package to the path
sys.path.insert(0, str(Path(__file__).parent))

from poster_analyzer import PosterAnalyzer, EventData


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('poster_analyzer.log', encoding='utf-8')
        ]
    )


def get_image_files(path: str) -> List[str]:
    """
    Get list of image files from path.
    
    Args:
        path: File path or directory path
        
    Returns:
        List of image file paths
    """
    path_obj = Path(path)
    
    if path_obj.is_file():
        if path_obj.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            return [str(path_obj)]
        else:
            raise ValueError(f"Unsupported image format: {path_obj.suffix}")
    
    elif path_obj.is_dir():
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(path_obj.glob(f'*{ext}'))
            image_files.extend(path_obj.glob(f'*{ext.upper()}'))
        
        return [str(f) for f in sorted(image_files)]
    
    else:
        raise FileNotFoundError(f"Path not found: {path}")


async def analyze_single_poster(analyzer: PosterAnalyzer, image_path: str, 
                              output_dir: str = None) -> EventData:
    """
    Analyze a single poster image.
    
    Args:
        analyzer: PosterAnalyzer instance
        image_path: Path to the image
        output_dir: Optional output directory for results
        
    Returns:
        EventData object
    """
    print(f"\\nAnalyzing: {Path(image_path).name}")
    print("-" * 50)
    
    event_data = await analyzer.analyze_poster(image_path)
    
    if event_data:
        # Print summary
        print(f"✅ Event extracted: {event_data.veranstaltungsname}")
        print(f"📍 Location: {event_data.ort.veranstaltungsort or 'N/A'}")
        print(f"📅 Date: {event_data.termine.beginn.strftime('%d.%m.%Y %H:%M') if event_data.termine.beginn else 'N/A'}")
        print(f"💰 Price: {'Kostenlos' if event_data.preise.kostenlos else f'{event_data.preise.preis}€' if event_data.preise.preis else 'N/A'}")
        print(f"🎭 Category: {event_data.kategorie.value}")
        print(f"🎯 Confidence: {event_data.metadaten.vertrauenswuerdigkeit:.2f}")
        
        if event_data.erkannte_qr_codes:
            print(f"📱 QR Codes: {len(event_data.erkannte_qr_codes)}")
        
        if event_data.erkannte_links:
            print(f"🔗 URLs: {len(event_data.erkannte_links)}")
        
        # Export results if output directory specified
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Create filename from image name
            base_name = Path(image_path).stem
            json_file = output_path / f"{base_name}_analysis.json"
            
            analyzer.export_results(event_data, str(json_file), 'json')
            print(f"💾 Results saved to: {json_file}")
        
        return event_data
    
    else:
        print("❌ Analysis failed - no event data extracted")
        return None


async def analyze_batch(analyzer: PosterAnalyzer, image_paths: List[str],
                       output_dir: str = None, max_concurrent: int = 3) -> List[EventData]:
    """
    Analyze multiple posters in batch.
    
    Args:
        analyzer: PosterAnalyzer instance
        image_paths: List of image paths
        output_dir: Optional output directory
        max_concurrent: Maximum concurrent analyses
        
    Returns:
        List of EventData objects
    """
    print(f"\\n🚀 Starting batch analysis of {len(image_paths)} posters")
    print(f"📊 Max concurrent: {max_concurrent}")
    print("=" * 60)
    
    # Analyze all posters
    results = await analyzer.analyze_multiple_posters(image_paths, max_concurrent)
    
    print("\\n📈 Batch Analysis Results")
    print("=" * 40)
    print(f"✅ Successful: {len(results)}/{len(image_paths)}")
    
    if results:
        # Print summary statistics
        categories = {}
        prices = []
        confidence_scores = []
        
        for event in results:
            # Category distribution
            cat = event.kategorie.value
            categories[cat] = categories.get(cat, 0) + 1
            
            # Price statistics
            if event.preise.preis:
                prices.append(event.preise.preis)
            
            # Confidence scores
            confidence_scores.append(event.metadaten.vertrauenswuerdigkeit)
        
        print(f"🎭 Categories: {dict(sorted(categories.items()))}")
        
        if prices:
            avg_price = sum(prices) / len(prices)
            print(f"💰 Average Price: {avg_price:.2f}€")
            print(f"💰 Price Range: {min(prices):.2f}€ - {max(prices):.2f}€")
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        print(f"🎯 Average Confidence: {avg_confidence:.2f}")
        
        # Export batch results
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Export individual results
            for i, (event, image_path) in enumerate(zip(results, image_paths)):
                base_name = Path(image_path).stem
                json_file = output_path / f"{base_name}_analysis.json"
                analyzer.export_results(event, str(json_file), 'json')
            
            # Export batch summary
            batch_summary = {
                'total_analyzed': len(image_paths),
                'successful_extractions': len(results),
                'success_rate': len(results) / len(image_paths),
                'categories': categories,
                'average_confidence': avg_confidence,
                'events': [event.to_dict() for event in results]
            }
            
            summary_file = output_path / 'batch_summary.json'
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(batch_summary, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"💾 Batch results exported to: {output_dir}")
    
    return results


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Event Poster Analyzer - Extract event information from poster images using Claude AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --image poster.jpg --api-key sk-ant-...
  python main.py --batch images/ --api-key sk-ant-... --output results/
  python main.py --image poster.jpg --api-key sk-ant-... --no-web-scraping --verbose
        """
    )
    
    # Input arguments
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--image', type=str, help='Single poster image to analyze')
    input_group.add_argument('--batch', type=str, help='Directory containing poster images')
    
    # Configuration arguments
    parser.add_argument('--api-key', type=str, required=True,
                       help='Claude API key (or set CLAUDE_API_KEY environment variable)')
    parser.add_argument('--output', type=str, help='Output directory for results')
    parser.add_argument('--max-concurrent', type=int, default=3,
                       help='Maximum concurrent analyses for batch processing')
    parser.add_argument('--no-web-scraping', action='store_true',
                       help='Disable web scraping enhancement')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Get API key from argument or environment
        api_key = args.api_key or os.getenv('CLAUDE_API_KEY')
        if not api_key:
            raise ValueError("Claude API key required. Use --api-key or set CLAUDE_API_KEY environment variable.")
        
        # Initialize analyzer
        logger.info("Initializing PosterAnalyzer...")
        analyzer = PosterAnalyzer(
            claude_api_key=api_key,
            enable_web_scraping=not args.no_web_scraping
        )
        
        # Determine input images
        if args.image:
            image_paths = get_image_files(args.image)
            if len(image_paths) == 1:
                # Single image analysis
                await analyze_single_poster(analyzer, image_paths[0], args.output)
            else:
                # Multiple images from pattern
                await analyze_batch(analyzer, image_paths, args.output, args.max_concurrent)
        
        elif args.batch:
            image_paths = get_image_files(args.batch)
            if not image_paths:
                raise ValueError(f"No image files found in: {args.batch}")
            
            await analyze_batch(analyzer, image_paths, args.output, args.max_concurrent)
        
        print("\\n🎉 Analysis complete!")
        
    except KeyboardInterrupt:
        print("\\n⏹️  Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Handle Windows asyncio event loop issues
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())