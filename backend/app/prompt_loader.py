from pathlib import Path
from typing import Any, Dict

class PromptLoader:
 def __init__(self, root=None): self.root=Path(root or Path(__file__).parents[1]/'prompts')
 def load(self, name: str, variables: Dict[str, Any] = None) -> str:
  path=self.root/(name+'.md')
  text=path.read_text(encoding='utf-8') if path.exists() else 'Return valid structured JSON.'
  for key,value in (variables or {}).items(): text=text.replace('{{'+key+'}}',str(value))
  return text
prompt_loader=PromptLoader()
