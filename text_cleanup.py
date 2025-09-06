#!/usr/bin/env python3
"""
Text Cleanup System
Multi-language patterns for cleaning extracted article content.
"""

import re
import yaml
import os

class MultiLanguageTextCleaner:
    def __init__(self):
        self.cleanup_patterns = {
            'french': {
                'subscription_walls': [
                    r'Il vous reste \d+[.,]\d*% de cet article à lire.*',
                    r'La suite est réservée aux abonnés.*',
                    r'Article réservé à nos abonnés.*',
                    r'Pour lire la suite.*abonnez-vous.*',
                    r'Cet article est réservé aux abonnés.*',
                    r'Le contenu auquel vous tentez d\'accéder.*abonné.*',
                    r'\*\*Il vous reste \d+.*à lire\*\*',
                    r'Accès illimité.*à partir de.*€.*'
                ],
                
                'navigation_elements': [
                    r'Lire aussi.*?\|.*?Article réservé.*',
                    r'Lire aussi la tribune.*?\|.*',
                    r'Lire plus tard.*',
                    r'Lire la suite.*',
                    r'Voir aussi.*?\|.*',
                    r'À lire également.*',
                    r'Dans le même dossier.*',
                    r'Sur le même sujet.*'
                ],
                
                'social_sharing': [
                    r'Partager cet article.*',
                    r'Partager sur Facebook.*',
                    r'Partager sur Twitter.*',
                    r'Suivez.*?sur.*',
                    r'Retrouvez.*?sur.*',
                    r'Rejoignez.*?sur.*',
                    r'@[A-Za-z0-9_]+'  # Twitter handles
                ],
                
                'newsletter_promotional': [
                    r'Recevez.*?newsletter.*',
                    r'S\'abonner.*?à partir de.*€.*',
                    r'Abonnez-vous.*',
                    r'Newsletter.*gratuite.*',
                    r'Inscrivez-vous.*newsletter.*',
                    r'Découvrez nos offres.*abonnement.*'
                ],
                
                'footer_elements': [
                    r'Le Monde.*Tous droits réservés.*',
                    r'Copyright.*Le Monde.*',
                    r'Mentions légales.*',
                    r'Politique de confidentialité.*',
                    r'Conditions générales.*',
                    r'CGU.*CGV.*'
                ],
                
                'editorial_notes': [
                    r'\(.*?Mis à jour.*?\)',
                    r'\(.*?Publié.*?\)',
                    r'\(.*?Modifié.*?\)',
                    r'Par\s+[A-Z][a-z]+\s+[A-Z][a-z]+.*',  # Author bylines
                    r'Édité par.*',
                    r'Relu par.*'
                ]
            },
            
            'romanian': {
                'subscription_walls': [
                    r'Restul articolului este rezervat abonaților.*',
                    r'Pentru a citi restul articolului.*abonează-te.*',
                    r'Articol disponibil doar pentru abonați.*',
                    r'Conținutul complet.*doar pentru abonați.*',
                    r'Acest articol este disponibil doar.*',
                    r'Pentru a accesa conținutul complet.*',
                    r'\*\*Îți mai rămân \d+.*de citit\*\*',
                    r'Abonament de la.*lei.*'
                ],
                
                'navigation_elements': [
                    r'Citește și:.*',
                    r'Vezi și:.*',
                    r'Citește mai mult.*',
                    r'Continuă citirea.*',
                    r'În același subiect.*',
                    r'Articole similare.*',
                    r'Pe același subiect.*',
                    r'De asemenea:.*'
                ],
                
                'social_sharing': [
                    r'Distribuie acest articol.*',
                    r'Distribuie pe Facebook.*',
                    r'Distribuie pe Twitter.*',
                    r'Urmărește.*?pe.*',
                    r'Găsește.*?pe.*',
                    r'Alătură-te.*?pe.*',
                    r'@[A-Za-z0-9_]+'  # Social media handles
                ],
                
                'newsletter_promotional': [
                    r'Primește newsletter.*',
                    r'Abonează-te.*newsletter.*',
                    r'Înscrie-te.*newsletter.*',
                    r'Newsletter.*gratuit.*',
                    r'Află primul.*newsletter.*',
                    r'Descoperă ofertele.*abonament.*'
                ],
                
                'footer_elements': [
                    r'Toate drepturile rezervate.*',
                    r'Copyright.*',
                    r'Termeni și condiții.*',
                    r'Politica de confidențialitate.*',
                    r'Contact.*redacție.*',
                    r'Despre noi.*'
                ],
                
                'editorial_notes': [
                    r'\(.*?Actualizat.*?\)',
                    r'\(.*?Publicat.*?\)',
                    r'\(.*?Modificat.*?\)',
                    r'De\s+[A-Z][a-z]+\s+[A-Z][a-z]+.*',  # Author bylines
                    r'Editor:.*',
                    r'Autor:.*'
                ]
            },
            
            'english': {
                'subscription_walls': [
                    r'You have \d+% of this article remaining.*',
                    r'This content is for subscribers only.*',
                    r'Subscribe to continue reading.*',
                    r'To read the full article.*subscribe.*',
                    r'Premium content.*subscribers only.*',
                    r'\*\*You have \d+.*remaining\*\*',
                    r'Subscription from.*\$.*month.*'
                ],
                
                'navigation_elements': [
                    r'Read also:.*',
                    r'See also:.*',
                    r'Read more.*',
                    r'Continue reading.*',
                    r'Related articles.*',
                    r'On the same topic.*',
                    r'You might also like.*'
                ],
                
                'social_sharing': [
                    r'Share this article.*',
                    r'Share on Facebook.*',
                    r'Share on Twitter.*',
                    r'Follow.*?on.*',
                    r'Find.*?on.*',
                    r'Join.*?on.*',
                    r'@[A-Za-z0-9_]+'
                ],
                
                'newsletter_promotional': [
                    r'Get our newsletter.*',
                    r'Subscribe.*newsletter.*',
                    r'Sign up.*newsletter.*',
                    r'Free newsletter.*',
                    r'Be the first.*newsletter.*',
                    r'Discover.*subscription.*'
                ]
            }
        }
        
        # Universal patterns that work across languages
        self.universal_patterns = {
            'social_media': [
                r'@[a-zA-Z0-9_]+',           # Twitter/social handles
                r'#[a-zA-Z0-9_]+',           # Hashtags
                r'bit\.ly/[a-zA-Z0-9]+',     # Short URLs
                r'tinyurl\.com/[a-zA-Z0-9]+' # Short URLs
            ],
            
            'urls_and_links': [
                r'https?://[^\s]+',          # Full URLs
                r'www\.[^\s]+',              # www links
                r'\[.*?\]\(.*?\)',           # Markdown links
                r'<a\s+[^>]*>.*?</a>'        # HTML links (if any remain)
            ],
            
            'percentage_indicators': [
                r'^\d+[.,]\d*%.*',           # Lines starting with percentages
                r'.*\d+[.,]\d*%.*remaining.*', # Content remaining indicators
                r'.*\d+[.,]\d*%.*ramaining.*'  # Common typo
            ],
            
            'subscription_indicators': [
                r'.*paywall.*',
                r'.*premium.*content.*',
                r'.*subscriber.*only.*',
                r'.*subscription.*required.*'
            ],
            
            'navigation_breadcrumbs': [
                r'^[A-Z][a-z]+\s*[|\>]\s*[A-Z][a-z]+.*',  # "News | Politics"
                r'^Home\s*[|\>].*',                        # "Home > News > Article"
                r'.*\s*[|\>]\s*Article$'                   # "... > Article"
            ],
            
            'advertisement_markers': [
                r'Advertisement',
                r'Sponsored Content',
                r'Promoted Post',
                r'Publicité',
                r'Reclamă',
                r'Anunț comercial'
            ]
        }

    def detect_language(self, text, domain=""):
        """Detect language from text and domain"""
        if domain.endswith('.ro'):
            return 'romanian'
        elif domain.endswith('.fr'):
            return 'french'
        elif domain.endswith(('.com', '.org', '.net', '.uk', '.us')):
            return 'english'
        
        # Simple language detection based on common words
        text_lower = text.lower()
        
        # Romanian indicators
        if any(word in text_lower for word in ['și', 'cu', 'pentru', 'este', 'sunt', 'într-un', 'într-o']):
            return 'romanian'
        
        # French indicators
        if any(word in text_lower for word in ['avec', 'pour', 'dans', 'cette', 'vous', 'nous', 'être']):
            return 'french'
        
        # Default to English
        return 'english'

    def clean_text(self, text, language=None, domain="", stop_at_paywall=True):
        """Main text cleaning function"""
        if language is None:
            language = self.detect_language(text, domain)
        
        original_text = text
        lines = text.split('\n')
        cleaned_lines = []
        
        # Get patterns for detected language
        patterns = self.cleanup_patterns.get(language, {})
        
        paywall_hit = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for paywall/subscription wall
            if stop_at_paywall and not paywall_hit:
                paywall_patterns = patterns.get('subscription_walls', [])
                for pattern in paywall_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        paywall_hit = True
                        print(f"Paywall detected, stopping at: {line[:100]}...")
                        break
                
                if paywall_hit:
                    break
            
            # Skip lines matching cleanup patterns
            should_skip = False
            
            # Check language-specific patterns
            for category, category_patterns in patterns.items():
                if category == 'subscription_walls':  # Already handled above
                    continue
                    
                for pattern in category_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        should_skip = True
                        break
                if should_skip:
                    break
            
            # Check universal patterns
            if not should_skip:
                for category, category_patterns in self.universal_patterns.items():
                    for pattern in category_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            should_skip = True
                            break
                    if should_skip:
                        break
            
            # Keep line if it passes all filters
            if not should_skip:
                cleaned_lines.append(line)
        
        # Join cleaned lines
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Additional post-processing
        cleaned_text = self.post_process_text(cleaned_text)
        
        # Stats
        original_lines = len([l for l in original_text.split('\n') if l.strip()])
        cleaned_lines_count = len(cleaned_lines)
        
        print(f"Text cleaning: {original_lines} → {cleaned_lines_count} lines ({language})")
        if paywall_hit:
            print("Stopped at paywall/subscription barrier")
        
        return cleaned_text

    def post_process_text(self, text):
        """Final text cleaning and normalization"""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
        text = re.sub(r'[ \t]+', ' ', text)     # Normalize spaces
        text = re.sub(r' +\n', '\n', text)      # Remove trailing spaces
        
        # Remove very short lines (likely artifacts)
        lines = text.split('\n')
        filtered_lines = []
        for line in lines:
            line = line.strip()
            if len(line) > 3 or line == '':  # Keep empty lines for paragraph breaks
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines).strip()

    def get_cleanup_stats(self, original_text, cleaned_text):
        """Generate statistics about text cleaning"""
        original_words = len(original_text.split())
        cleaned_words = len(cleaned_text.split())
        original_lines = len([l for l in original_text.split('\n') if l.strip()])
        cleaned_lines = len([l for l in cleaned_text.split('\n') if l.strip()])
        
        return {
            'original_words': original_words,
            'cleaned_words': cleaned_words,
            'words_removed': original_words - cleaned_words,
            'original_lines': original_lines,
            'cleaned_lines': cleaned_lines,
            'lines_removed': original_lines - cleaned_lines,
            'reduction_percentage': ((original_words - cleaned_words) / original_words * 100) if original_words > 0 else 0
        }

    def load_domain_cleanup_rules(self, domain):
        """Load domain-specific cleanup rules from config file"""
        config_file = os.path.join("extraction_rules", f"{domain}.yaml")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    return config.get('cleanup_patterns', {})
            except Exception as e:
                print(f"Warning: Could not load cleanup rules for {domain}: {e}")
        return {}

    def clean_with_domain_rules(self, text, domain):
        """Clean text using domain-specific rules"""
        domain_rules = self.load_domain_cleanup_rules(domain)
        if not domain_rules:
            return self.clean_text(text, domain=domain)
        
        # Apply domain-specific patterns first
        for category, patterns in domain_rules.items():
            for pattern in patterns:
                text = re.sub(pattern, '', text, flags=re.MULTILINE | re.IGNORECASE)
        
        # Then apply universal cleaning
        return self.clean_text(text, domain=domain)


if __name__ == "__main__":
    # Test the text cleaning system
    cleaner = MultiLanguageTextCleaner()
    
    # Test French text with paywall
    french_text = """
    Nous écrivons pour exprimer notre vive inquiétude concernant la famine qui se propage à Gaza.
    
    Lire aussi la tribune | Article réservé à nos abonnés
    
    Ces dernières semaines, le Programme alimentaire mondial de l'ONU a averti.
    
    Il vous reste 55.6% de cet article à lire. La suite est réservée aux abonnés.
    
    This content should not appear in the cleaned version.
    """
    
    print("=== Testing French text cleaning ===")
    cleaned = cleaner.clean_text(french_text, language='french')
    print("Cleaned text:")
    print(cleaned)
    print()
    
    # Test Romanian text
    romanian_text = """
    Acesta este un articol important despre știrile din România.
    
    Citește și: Alt articol interesant
    
    Conținutul principal al articolului continuă aici.
    
    Restul articolului este rezervat abonaților. Pentru a citi restul.
    
    This should be removed.
    """
    
    print("=== Testing Romanian text cleaning ===")
    cleaned_ro = cleaner.clean_text(romanian_text, language='romanian')
    print("Cleaned text:")
    print(cleaned_ro)