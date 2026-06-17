import glob
import re

def fix_max_tokens(content):
    pattern = r'if "max_tokens" in (params_[a-zA-Z0-9]+):\s*([a-zA-Z0-9_]+)\["max_tokens"\] = \1\["max_tokens"\]'
    
    def repl(m):
        params_dict = m.group(1)
        kwargs_dict = m.group(2)
        # Using simple inline string replacement logic to keep indentation clean
        replacement = (
            f'if "max_tokens" in {params_dict}:\n'
            f'                                if any(m in {params_dict}["model"] for m in ["gpt-5", "o1", "o3"]): {kwargs_dict}["max_completion_tokens"] = {params_dict}["max_tokens"]\n'
            f'                                else: {kwargs_dict}["max_tokens"] = {params_dict}["max_tokens"]'
        )
        return replacement

    new_content = re.sub(pattern, repl, content)
    return new_content

for filepath in glob.glob('steps/*.py'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    new_content = fix_max_tokens(content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Fixed {filepath}')
