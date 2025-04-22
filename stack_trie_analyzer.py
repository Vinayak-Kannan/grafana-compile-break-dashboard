import re
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple
import json

class StackTrieAnalyzer:
    def __init__(self, html_file: str):
        with open(html_file, 'r') as f:
            self.soup = BeautifulSoup(f.read(), 'html.parser')
        
    def parse_stack_trie(self) -> List[Dict]:
        stack_trie_div = self.soup.find('div', class_='stack-trie')
        if not stack_trie_div:
            return []
        
        stacks = []
        current_stack = []

        for li in stack_trie_div.find_all('li'):
            stack_info = self._parse_stack_item(li)
            if stack_info:
                current_stack.append(stack_info)
        
        stacks.append(current_stack)
        return stacks
    
    def _parse_stack_item(self, li) -> Dict:
        # Extract file and line information
        file_line = li.get_text().strip()
        if not file_line:
            return None
            
        # Extract compilation status and ID
        status_link = li.find('a')
        if not status_link:
            return None
            
        status = status_link.get('class', [])[0] if status_link.get('class') else None
        comp_id = status_link.get_text().strip()
        
        return {
            'file_line': file_line,
            'status': status,
            'compilation_id': comp_id
        }
    
    def analyze_compilations(self):
        stacks = self.parse_stack_trie()
        
        print("\nStack Trie Analysis:")
        print("=" * 50)
        
        for stack in stacks:
            print("\nStack Trace:")
            for item in stack:
                status_color = {
                    'status-ok': 'Green (Success)',
                    'status-break': 'Light Green (Graph Break)',
                    'status-error': 'Red (Error)',
                    'status-empty': 'White (Empty)',
                    'status-missing': 'Purple (Missing)'
                }.get(item['status'], 'Unknown')
                
                print(f"\nFile/Line: {item['file_line']}")
                print(f"Compilation ID: {item['compilation_id']}")
                print(f"Status: {status_color}")
                
                # Analyze recompilations
                if '_' in item['compilation_id']:
                    print("Note: This is a recompilation (indicated by _ in compilation ID)")
                
                # Analyze graph breaks
                if item['status'] == 'status-break':
                    print("Note: This is a graph break")

def main():
    analyzer = StackTrieAnalyzer('tl_out/index.html')
    analyzer.analyze_compilations()

if __name__ == "__main__":
    main() 