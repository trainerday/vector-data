#!/usr/bin/env python3
"""
Sitemap Generation Functions
Generate final sitemap structure with all enhancements
"""

import json
from pathlib import Path
from typing import List, Dict

class SitemapGenerator:
    def __init__(self):
        pass
    
    def generate_final_sitemap(
        self, 
        enhanced_pages: List[Dict], 
        common_elements: Dict, 
        output_dir: Path,
        final_output_dir: Path = None,
        video_name: str = "web_full",
        processing_metadata: Dict = None
    ) -> Dict:
        """
        Generate final sitemap structure with all enhancements
        
        Args:
            enhanced_pages: List of AI-enhanced page data
            common_elements: Common UI elements across pages
            output_dir: Directory to save final sitemap
            processing_metadata: Optional metadata about processing
        
        Returns:
            Final sitemap structure
        """
        print(f"Generating final sitemap from {len(enhanced_pages)} enhanced pages...")
        
        # Create processing info
        processing_info = {
            "source_method": "Complete Video Processing Pipeline",
            "total_pages": len(enhanced_pages),
            "total_sentences": sum(len(page.get('sentences', [])) for page in enhanced_pages),
            "enhancement_method": "OpenAI Vision Analysis with User Context",
            "processing_date": None  # Would be set by caller
        }
        
        if processing_metadata:
            processing_info.update(processing_metadata)
        
        # Create final structure
        final_sitemap = {
            "processing_info": processing_info,
            "common_elements": common_elements,
            "pages": enhanced_pages
        }
        
        # Determine final output paths
        if final_output_dir:
            final_output_dir.mkdir(parents=True, exist_ok=True)
            final_sitemap_path = final_output_dir / f"{video_name}_site_map.json"
        else:
            final_sitemap_path = output_dir / "final_sitemap.json"
        
        # Save final sitemap
        sitemap_path = output_dir / "final_sitemap.json"
        with open(sitemap_path, 'w') as f:
            json.dump(final_sitemap, f, indent=2)
        
        # Also save to final location with proper naming
        if final_output_dir:
            with open(final_sitemap_path, 'w') as f:
                json.dump(final_sitemap, f, indent=2)
            print(f"✅ Final sitemap generated!")
            print(f"Saved to: {final_sitemap_path}")
        else:
            print(f"✅ Final sitemap generated!")
            print(f"Saved to: {sitemap_path}")
        
        # Generate summary statistics
        stats = self._generate_sitemap_statistics(final_sitemap)
        
        # Save statistics
        stats_path = output_dir / "sitemap_statistics.json"
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"Statistics saved to: {stats_path}")
        
        return final_sitemap
    
    def _generate_sitemap_statistics(self, sitemap: Dict) -> Dict:
        """Generate comprehensive statistics about the sitemap"""
        pages = sitemap.get('pages', [])
        
        # Basic counts
        total_pages = len(pages)
        total_sentences = sum(page.get('total_sentences', 0) for page in pages)
        
        # Page statistics
        page_stats = []
        for page in pages:
            sentences = page.get('sentences', [])
            
            # Count successful AI analyses
            successful_analyses = sum(
                1 for s in sentences 
                if s.get('ai_analysis', {}).get('comprehensive_page_description') != "Analysis unavailable"
            )
            
            # Count screenshots
            screenshots = sum(1 for s in sentences if s.get('screenshot'))
            
            page_stats.append({
                "page_name": page.get('page_name'),
                "sentence_count": len(sentences),
                "screenshot_count": screenshots,
                "successful_ai_analyses": successful_analyses,
                "relative_url": page.get('relative_url', 'unknown')
            })
        
        # Overall statistics
        total_screenshots = sum(stat['screenshot_count'] for stat in page_stats)
        total_ai_analyses = sum(stat['successful_ai_analyses'] for stat in page_stats)
        
        # UI elements analysis
        ui_elements = {}
        user_actions = {}
        
        for page in pages:
            for sentence in page.get('sentences', []):
                analysis = sentence.get('ai_analysis', {})
                
                # Count UI elements
                for element in analysis.get('ui_elements_detected', []):
                    ui_elements[element] = ui_elements.get(element, 0) + 1
                
                # Count user actions
                for action in analysis.get('possible_user_actions', []):
                    user_actions[action] = user_actions.get(action, 0) + 1
        
        return {
            "overview": {
                "total_pages": total_pages,
                "total_sentences": total_sentences,
                "total_screenshots": total_screenshots,
                "total_ai_analyses": total_ai_analyses,
                "average_sentences_per_page": total_sentences / total_pages if total_pages > 0 else 0
            },
            "page_statistics": page_stats,
            "ui_elements_frequency": dict(sorted(ui_elements.items(), key=lambda x: x[1], reverse=True)[:20]),
            "user_actions_frequency": dict(sorted(user_actions.items(), key=lambda x: x[1], reverse=True)[:20]),
            "coverage_metrics": {
                "pages_with_screenshots": sum(1 for stat in page_stats if stat['screenshot_count'] > 0),
                "pages_with_ai_analysis": sum(1 for stat in page_stats if stat['successful_ai_analyses'] > 0),
                "screenshot_coverage": total_screenshots / total_sentences * 100 if total_sentences > 0 else 0,
                "ai_analysis_coverage": total_ai_analyses / total_sentences * 100 if total_sentences > 0 else 0
            }
        }
    
    def create_legacy_format(self, final_sitemap: Dict, output_dir: Path) -> Dict:
        """
        Create a legacy format compatible with existing systems
        
        Args:
            final_sitemap: Final sitemap structure
            output_dir: Directory to save legacy format
        
        Returns:
            Legacy format sitemap
        """
        pages = final_sitemap.get('pages', [])
        
        # Convert to legacy sentence format
        legacy_sentences = []
        
        for page in pages:
            for sentence in page.get('sentences', []):
                legacy_sentence = {
                    "sentence_id": sentence.get('sentence_id'),
                    "sentence": sentence.get('user_description'),
                    "timestamp": sentence.get('timestamp'),
                    "screenshot": sentence.get('screenshot'),
                    "page_name": page.get('page_name'),
                    "relative_url": page.get('relative_url')
                }
                legacy_sentences.append(legacy_sentence)
        
        legacy_format = {
            "sentences": legacy_sentences,
            "total_sentences": len(legacy_sentences),
            "pages_detected": len(pages),
            "processing_info": final_sitemap.get('processing_info')
        }
        
        # Save legacy format
        legacy_path = output_dir / "legacy_sitemap_structure.json"
        with open(legacy_path, 'w') as f:
            json.dump(legacy_format, f, indent=2)
        
        print(f"Legacy format saved to: {legacy_path}")
        
        return legacy_format
    
    def validate_sitemap(self, sitemap: Dict) -> Dict:
        """
        Validate the final sitemap structure
        
        Args:
            sitemap: Final sitemap structure
        
        Returns:
            Validation results
        """
        issues = []
        pages = sitemap.get('pages', [])
        
        # Check basic structure
        if not pages:
            issues.append("No pages found in sitemap")
        
        # Check each page
        for i, page in enumerate(pages):
            page_name = page.get('page_name', f'Page {i}')
            
            if not page.get('sentences'):
                issues.append(f"Page '{page_name}' has no sentences")
            
            if page.get('relative_url') == 'unknown':
                issues.append(f"Page '{page_name}' has unknown URL")
            
            # Check sentences in page
            sentences = page.get('sentences', [])
            for j, sentence in enumerate(sentences):
                if not sentence.get('user_description'):
                    issues.append(f"Page '{page_name}', sentence {j}: missing user description")
                
                if not sentence.get('screenshot'):
                    issues.append(f"Page '{page_name}', sentence {j}: missing screenshot")
        
        # Check for common elements
        if not sitemap.get('common_elements'):
            issues.append("No common elements defined")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "total_issues": len(issues),
            "pages_validated": len(pages),
            "sentences_validated": sum(len(page.get('sentences', [])) for page in pages)
        }