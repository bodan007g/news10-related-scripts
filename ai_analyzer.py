#!/usr/bin/env python3
"""
AI Analyzer Script
Analyzes extracted article content using BART models for summarization, classification, and metadata generation.
"""

import os
import json
import yaml
import re
from datetime import datetime
from bart_llm_utils import bart_summarize_text, detect_domain_from_link
from content_filters import ContentTypeClassifier
import time

# Configuration
CONTENT_DIR = "content"
LOGS_DIR = "logs"
STATUS_FILE = "ai_analyzer_status.json"

# Domain categories for classification
DOMAIN_CATEGORIES = [
    "politic", "economic", "social", "sport", "health", "technology", 
    "culture", "international", "local", "environment", "education", "crime"
]

class AIAnalyzer:
    def __init__(self):
        self.processed_status = self.load_status()
        self.content_classifier = ContentTypeClassifier()
        self.stats = {
            'total_processed': 0,
            'successful_analysis': 0,
            'failed_analysis': 0,
            'already_processed': 0,
            'skipped_files': 0,
            'content_types_detected': {},
            'filtered_by_content_type': 0
        }

    def load_status(self):
        """Load processing status from file"""
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_status(self):
        """Save processing status to file"""
        with open(STATUS_FILE, 'w') as f:
            json.dump(self.processed_status, f, indent=2)

    def extract_named_entities(self, text):
        """Simple named entity extraction using pattern matching"""
        entities = {
            'persons': [],
            'locations': [],
            'organizations': []
        }
        
        # Simple patterns for French text - this can be improved with spaCy later
        # Person patterns (basic French names)
        person_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last
            r'\b[A-Z]\.\s*[A-Z][a-z]+\b',       # J. Doe
        ]
        
        # Location patterns
        location_patterns = [
            r'\b(?:Paris|Lyon|Marseille|Toulouse|Nice|Nantes|Strasbourg|Montpellier|Bordeaux|Lille|Rennes|Reims|Le Havre|Saint-Étienne|Toulon|Grenoble|Angers|Dijon|Nîmes|Aix-en-Provence|Brest|Le Mans|Amiens|Tours|Limoges|Clermont-Ferrand|Villeurbanne|Besançon)\b',
            r'\b(?:France|Allemagne|Italie|Espagne|Portugal|Belgique|Suisse|Luxembourg|Royaume-Uni|États-Unis|Canada|Chine|Japon|Russie|Inde|Brésil|Argentine|Mexique|Australie|Afrique du Sud)\b',
            r'\b(?:Europe|Asie|Afrique|Amérique|Océanie)\b',
            r'\b(?:Gaza|Israël|Palestine|Ukraine|Russie|Syrie|Irak|Afghanistan|Iran)\b'  # Current hot spots
        ]
        
        # Organization patterns
        org_patterns = [
            r'\b(?:ONU|UNESCO|OTAN|UE|Commission européenne|Parlement européen|Assemblée nationale|Sénat|Élysée|Matignon)\b',
            r'\b(?:Apple|Google|Microsoft|Amazon|Facebook|Meta|Twitter|Tesla|BMW|Mercedes|Volkswagen|Airbus|Total|LVMH|L\'Oréal)\b',
            r'\b[A-Z][A-Za-z]*\s+(?:SA|SAS|SARL|Inc|Corp|Ltd|AG|GmbH)\b'
        ]
        
        # Extract entities
        for pattern in person_patterns:
            matches = re.findall(pattern, text)
            entities['persons'].extend(matches)
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities['locations'].extend([m.capitalize() for m in matches])
        
        for pattern in org_patterns:
            matches = re.findall(pattern, text)
            entities['organizations'].extend(matches)
        
        # Remove duplicates and clean up
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities

    def analyze_sentiment(self, text):
        """Simple sentiment analysis based on keywords"""
        # Simple French sentiment keywords
        positive_words = [
            'réussite', 'succès', 'victoire', 'progrès', 'amélioration', 'développement',
            'croissance', 'augmentation', 'hausse', 'gain', 'bénéfice', 'prospérité',
            'innovation', 'modernisation', 'excellence', 'qualité'
        ]
        
        negative_words = [
            'crise', 'problème', 'difficulté', 'échec', 'perte', 'baisse', 'chute',
            'diminution', 'réduction', 'conflit', 'guerre', 'violence', 'accident',
            'catastrophe', 'danger', 'risque', 'menace', 'inquiétude', 'préoccupation',
            'corruption', 'scandale', 'polémique'
        ]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'

    def calculate_importance_score(self, text, metadata):
        """Calculate article importance score based on various factors"""
        score = 0.5  # Base score
        
        # Length factor
        word_count = len(text.split())
        if word_count > 1000:
            score += 0.2
        elif word_count > 500:
            score += 0.1
        elif word_count < 100:
            score -= 0.3
        
        # Content quality indicators
        text_lower = text.lower()
        
        # Important keywords that boost importance
        important_keywords = [
            'gouvernement', 'président', 'ministre', 'parlement', 'élection',
            'économie', 'crise', 'guerre', 'paix', 'accord', 'traité',
            'innovation', 'découverte', 'recherche', 'technologie', 'santé',
            'climat', 'environnement', 'éducation', 'culture'
        ]
        
        keyword_matches = sum(1 for word in important_keywords if word in text_lower)
        score += min(keyword_matches * 0.05, 0.3)  # Max 0.3 boost
        
        # Reduce score for certain types of content
        low_value_patterns = [
            'guide d\'achat', 'meilleur', 'comparatif', 'test', 'avis',
            'accident de voiture', 'faits divers', 'people', 'célébrité'
        ]
        
        for pattern in low_value_patterns:
            if pattern in text_lower:
                score -= 0.2
                break
        
        # Title analysis
        title = metadata.get('title', '').lower()
        if any(word in title for word in ['urgent', 'alerte', 'exclusif', 'breaking']):
            score += 0.2
        
        # Ensure score stays within bounds
        return max(0.0, min(1.0, score))

    def determine_geographic_scope(self, text, entities):
        """Determine the geographic scope of the article"""
        text_lower = text.lower()
        locations = [loc.lower() for loc in entities.get('locations', [])]
        
        # Local indicators
        local_keywords = ['iași', 'iasi', 'moldavie', 'moldova', 'românia', 'romania', 'roumanie']
        if any(keyword in text_lower for keyword in local_keywords):
            return 'local'
        
        # National indicators
        national_keywords = ['france', 'français', 'nationale', 'gouvernement français', 'paris']
        if any(keyword in text_lower for keyword in national_keywords) and not any('international' in text_lower for _ in [1]):
            return 'national'
        
        # International indicators
        international_keywords = ['international', 'mondial', 'europe', 'union européenne', 'otan', 'onu']
        if any(keyword in text_lower for keyword in international_keywords) or len(locations) > 2:
            return 'international'
        
        # Regional by default
        return 'regional'

    def analyze_content(self, markdown_file, metadata_file):
        """Analyze content and enhance metadata"""
        # Check if already processed
        file_key = f"{metadata_file}"
        if file_key in self.processed_status and self.processed_status[file_key]['status'] == 'success':
            self.stats['already_processed'] += 1
            return
        
        try:
            # Read markdown content
            with open(markdown_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Read existing metadata
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = yaml.safe_load(f)
            
            # Skip if content is too short
            if len(content.strip()) < 100:
                self.stats['skipped_files'] += 1
                self.processed_status[file_key] = {
                    'status': 'skipped',
                    'reason': 'Content too short for AI analysis',
                    'processed_at': datetime.now().isoformat()
                }
                return
            
            # Classify content type using BART
            url = metadata.get('url', '')
            content_type, content_confidence = self.content_classifier.classify_content(content[:1000], url)
            
            # Track content type statistics
            if content_type not in self.stats['content_types_detected']:
                self.stats['content_types_detected'][content_type] = 0
            self.stats['content_types_detected'][content_type] += 1
            
            # Skip non-news content
            if not self.content_classifier.should_keep_content(content_type, content_confidence):
                self.stats['filtered_by_content_type'] += 1
                self.processed_status[file_key] = {
                    'status': 'filtered',
                    'reason': f'Content type: {content_type} (confidence: {content_confidence:.2f})',
                    'processed_at': datetime.now().isoformat()
                }
                print(f"FILTERED: {metadata.get('title', 'Untitled')} - Type: {content_type}")
                return
            
            print(f"Analyzing: {metadata.get('title', 'Untitled')} - Type: {content_type}")
            
            # Generate summary using BART
            try:
                # Limit content length for BART (max ~1000 tokens)
                content_for_summary = content[:3000] if len(content) > 3000 else content
                summary = bart_summarize_text(content_for_summary, max_length=100, min_length=30)
                if not summary:
                    summary = content[:200] + "..." if len(content) > 200 else content
            except Exception as e:
                print(f"Error generating summary: {e}")
                summary = content[:200] + "..." if len(content) > 200 else content
            
            # Detect domain/category using BART
            try:
                url = metadata.get('url', '')
                # Extract URL path for classification
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                url_path = parsed_url.path
                
                domain_result = detect_domain_from_link(url_path)
                # Parse the result which comes as "Domeniu: category (scor: 0.xx)"
                if "Domeniu:" in domain_result:
                    category = domain_result.split("Domeniu:")[1].split("(")[0].strip()
                    # Map Romanian to English categories
                    category_mapping = {
                        'economic': 'economic',
                        'politic': 'politic', 
                        'social': 'social',
                        'sport': 'sport',
                        'tehnologie': 'technology',
                        'educatie': 'education',
                        'sanatate': 'health',
                        'cultural': 'culture',
                        'international': 'international'
                    }
                    category = category_mapping.get(category, 'general')
                else:
                    category = 'general'
            except Exception as e:
                print(f"Error detecting category: {e}")
                category = 'general'
            
            # Extract named entities
            entities = self.extract_named_entities(content)
            
            # Analyze sentiment
            sentiment = self.analyze_sentiment(content)
            
            # Calculate importance score
            importance_score = self.calculate_importance_score(content, metadata)
            
            # Determine geographic scope
            geographic_scope = self.determine_geographic_scope(content, entities)
            
            # Calculate complexity score (simple metric based on sentence length, vocabulary)
            sentences = content.split('.')
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
            unique_words = len(set(content.lower().split()))
            total_words = len(content.split())
            vocabulary_richness = unique_words / total_words if total_words > 0 else 0
            
            complexity_score = min(1.0, (avg_sentence_length / 20 + vocabulary_richness) / 2)
            
            # Update metadata with AI analysis
            ai_metadata = {
                'summary': summary,
                'entities': entities,
                'sentiment': sentiment,
                'importance_score': round(importance_score, 2),
                'categories': [category],
                'content_type': content_type,
                'content_type_confidence': round(content_confidence, 2),
                'language': 'fr',  # Assuming French for Le Monde
                'word_count': len(content.split()),
                'complexity_score': round(complexity_score, 2),
                'geographic_scope': geographic_scope,
                'ai_processed_at': datetime.now().isoformat(),
                'extraction_confidence': 0.8  # Default confidence
            }
            
            # Merge with existing metadata
            metadata.update(ai_metadata)
            
            # Save updated metadata
            with open(metadata_file, 'w', encoding='utf-8') as f:
                yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)
            
            # Update status
            self.processed_status[file_key] = {
                'status': 'success',
                'importance_score': importance_score,
                'category': category,
                'processed_at': datetime.now().isoformat()
            }
            
            self.stats['successful_analysis'] += 1
            print(f"✓ Analyzed: {metadata.get('title', 'Untitled')} - Score: {importance_score:.2f}")
            
        except Exception as e:
            print(f"Error analyzing {metadata_file}: {e}")
            self.stats['failed_analysis'] += 1
            
            self.processed_status[file_key] = {
                'status': 'error',
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            }
        
        self.stats['total_processed'] += 1

    def find_metadata_files(self):
        """Find all metadata files to process"""
        metadata_files = []
        if not os.path.exists(CONTENT_DIR):
            return metadata_files
        
        for root, dirs, files in os.walk(CONTENT_DIR):
            if 'metadata' in root:
                for file in files:
                    if file.endswith('.yaml'):
                        metadata_path = os.path.join(root, file)
                        # Find corresponding markdown file
                        markdown_path = metadata_path.replace('/metadata/', '/extracted/').replace('.yaml', '.md')
                        
                        if os.path.exists(markdown_path):
                            metadata_files.append((markdown_path, metadata_path))
        
        return metadata_files

    def run(self):
        """Main processing function"""
        start_time = time.time()
        print(f"AI Analyzer started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Find all metadata files to process
        metadata_files = self.find_metadata_files()
        if not metadata_files:
            print("No metadata files found to process")
            return
        
        print(f"Found {len(metadata_files)} files to analyze")
        
        # Process each file
        for markdown_file, metadata_file in metadata_files:
            self.analyze_content(markdown_file, metadata_file)
            
            # Small delay to avoid overwhelming the system
            time.sleep(0.1)
        
        # Save status and print summary
        self.save_status()
        
        elapsed = time.time() - start_time
        print(f"\n=== AI Analyzer Summary ===")
        print(f"Total files processed: {self.stats['total_processed']}")
        print(f"Successful analyses: {self.stats['successful_analysis']}")
        print(f"Failed analyses: {self.stats['failed_analysis']}")
        print(f"Already processed: {self.stats['already_processed']}")
        print(f"Skipped files: {self.stats['skipped_files']}")
        print(f"Filtered by content type: {self.stats['filtered_by_content_type']}")
        
        # Show content type breakdown
        if self.stats['content_types_detected']:
            print("Content types detected:")
            for content_type, count in self.stats['content_types_detected'].items():
                print(f"  {content_type}: {count} files")
        
        print(f"Total time: {elapsed:.2f} seconds")
        
        # Write summary to log
        self.write_summary_log(elapsed)

    def write_summary_log(self, elapsed_time):
        """Write processing summary to log file"""
        now = datetime.now()
        month_str = now.strftime("%Y-%m")
        month_dir = os.path.join(LOGS_DIR, month_str)
        os.makedirs(month_dir, exist_ok=True)
        
        summary_log_path = os.path.join(month_dir, "ai_analyzer_summary.log")
        
        log_entry = (
            f"{now.strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Processed: {self.stats['total_processed']} | "
            f"Analyzed: {self.stats['successful_analysis']} | "
            f"Failed: {self.stats['failed_analysis']} | "
            f"Skipped: {self.stats['skipped_files']} | "
            f"Time: {elapsed_time:.2f}s\n"
        )
        
        with open(summary_log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)

if __name__ == "__main__":
    analyzer = AIAnalyzer()
    analyzer.run()