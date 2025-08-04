import subprocess
import uuid
import os
import re
import glob

def is_print_only(code, language, expected_output=None):
    lines = [line.strip() for line in code.strip().split('\n') if line.strip()]

    if language == "python":
        logic_keywords = ["for", "while", "def", "return", "*", "/", "+", "-", "import", "math", "range", "="]
        has_logic = any(any(keyword in line for keyword in logic_keywords) for line in lines)
        print_statements = [line for line in lines if re.match(r'^print\s*\(.*\)$', line)]
        only_printing_literals = all(re.match(r'^print\s*\((\d+|["\'].*["\'])\)$', line) for line in print_statements)

        if print_statements and not has_logic and only_printing_literals:
            if expected_output and str(expected_output) in code:
                return True, "Respected Participant We Know You Are Very Very Brilliant: Don't Print the output Using Print Statement. Write the logic."
            else:
                return True, "Respected Participant We Know You Are Very Very Brilliant: Don't Print the output Using Print Statement. Write the logic."

    elif language == "javascript":
        logic_keywords = ["for", "while", "function", "return", "*", "/", "+", "-", "let", "const", "var", "="]
        has_logic = any(any(keyword in line for keyword in logic_keywords) for line in lines)
        print_statements = [line for line in lines if re.match(r'^console\.log\s*\(.*\);?$', line)]
        only_printing_literals = all(re.match(r'^console\.log\s*\((\d+|["\'`].*["\'`])\);?$', line) for line in print_statements)

        if print_statements and not has_logic and only_printing_literals:
            if expected_output and str(expected_output) in code:
                return True, "Respected Participant We Know You Are Very Very Brilliant: Don't Print the output Using Console.log() Statement. Write the logic."
            else:
                return True, "Respected Participant We Know You Are Very Very Brilliant: Don't Print the output Using Console.log() Statement. Write the logic."

    elif language == "java":
        logic_keywords = ["for", "while", "if", "return", "*", "/", "+", "-", "int", "double", "=", "Scanner", "Math"]
        has_logic = any(any(keyword in line for keyword in logic_keywords) for line in lines if "System.out.println" not in line)
        print_statements = [line for line in lines if "System.out.println" in line]
        only_printing_literals = all(
            re.match(r'System\.out\.println\s*\((\d+|["\'].*["\'])\);', line) for line in print_statements
        )

        if print_statements and not has_logic and only_printing_literals:
            if expected_output and str(expected_output) in code:
                return True, "Respected Participant We Know You Are Very Very Brilliant: Don't Print the output Using Print Statement. Write the logic."
            else:
                return True, "Respected Participant We Know You Are Very Very Brilliant: Don't Print the output Using Print Statement. Write the logic."

    elif language == "c":
        logic_keywords = ["for", "while", "*", "/", "+", "-", "scanf", "=", "int", "return"]
        has_logic = any(any(keyword in line for keyword in logic_keywords) for line in lines if "printf" not in line)
        print_statements = [line for line in lines if "printf" in line]
        only_printing_literals = all(
            re.match(r'printf\s*\(\s*(".*?"|\d+)\s*\)\s*;', line) for line in print_statements
        )

        if print_statements and not has_logic and only_printing_literals:
            if expected_output and str(expected_output) in code:
                return True, "Respected Participant We Know You Are Very Very Brilliant: Don't Print the output Using Printf Statement. Write the logic."
            else:
                return True, "Respected Participant We Know You Are Very Very Brilliant: Don't Print the output Using Printf Statement. Write the logic."

    return False, ""

def run_code(language, code, expected_output=None):
    only_print, message = is_print_only(code, language, expected_output)
    if only_print:
        return {"stdout": "", "stderr": message, "success": False}

    filename = f"{uuid.uuid4()}"
    files_to_delete = []

    try:
        if language == "python":
            filepath = f"{filename}.py"
            with open(filepath, "w") as f:
                f.write(code)
            cmd = ["python", filepath]
            files_to_delete.append(filepath)

        elif language == "c":
            filepath = f"{filename}.c"
            exe_file = f"{filename}.exe" if os.name == "nt" else f"./{filename}"
            with open(filepath, "w") as f:
                f.write(code)
            compile_proc = subprocess.run(["gcc", filepath, "-o", exe_file], capture_output=True, text=True, timeout=5)
            if compile_proc.returncode != 0:
                return {
                    "stdout": compile_proc.stdout.strip(),
                    "stderr": compile_proc.stderr.strip(),
                    "success": False
                }
            cmd = [exe_file]
            files_to_delete.extend([filepath, exe_file])

        elif language == "java":
            class_name = "Main"
            java_file = f"{class_name}.java"
            with open(java_file, "w") as f:
                if not re.search(r'public\s+class\s+Main', code):
                    f.write(f"public class {class_name} {{\n{code}\n}}")
                else:
                    f.write(code)
            compile_proc = subprocess.run(["javac", java_file], capture_output=True, text=True, timeout=5)
            if compile_proc.returncode != 0:
                return {
                    "stdout": compile_proc.stdout.strip(),
                    "stderr": compile_proc.stderr.strip(),
                    "success": False
                }
            cmd = ["java", class_name]
            files_to_delete.append(java_file)
            files_to_delete.extend(glob.glob(f"{class_name}*.class"))

        elif language == "javascript":
            filepath = f"{filename}.js"
            with open(filepath, "w") as f:
                f.write(code)
            cmd = ["node", filepath]
            files_to_delete.append(filepath)

        else:
            return {"error": "Unsupported language"}

        result = subprocess.run(cmd, capture_output=True, timeout=5, text=True)
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "success": result.returncode == 0
        }

    except subprocess.TimeoutExpired:
        return {"error": "Execution timed out"}
    except Exception as e:
        return {"error": str(e)}

    finally:
        for f in files_to_delete:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception as cleanup_error:
                    print(f"Cleanup error: {cleanup_error}")
