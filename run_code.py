import subprocess
import uuid
import os
import re

def is_print_only(code, language):
    lines = [line.strip() for line in code.strip().split('\n') if line.strip()]

    if language == "python":
        if all(re.match(r'^print\s*\(.*\)$', line) for line in lines):
            return True, "Respected Participant We Know You Are Brilliant: Please write logic, not just print statements."

    elif language == "javascript":
        if all(re.match(r'^console\.log\s*\(.*\);?$', line) for line in lines):
            return True, "Respected Participant We Know You Are Brilliant: Please write logic, console.log alone is not allowed."

    elif language == "java":
        print_calls = re.findall(r'System\.out\.println\s*\(.*\);', code)
        non_print_lines = [line for line in lines if "System.out.println" not in line and not re.match(r'^(public|class|static|void|\{|\}|import|package)', line)]
        if len(print_calls) > 0 and len(non_print_lines) == 0:
            return True, "Respected Participant We Know You Are Brilliant: Please write logic, Only System.out.println is not accepted."

    elif language == "c":
        print_calls = re.findall(r'printf\s*\(.*\);', code)
        non_print_lines = [line for line in lines if "printf" not in line and not re.match(r'^(#include|int\s+main|\{|\}|return|void)', line)]
        if len(print_calls) > 0 and len(non_print_lines) == 0:
            return True, "Respected Participant We Know You Are Brilliant : Only printf found. Add some logic too."

    return False, ""

def run_code(language, code):
    only_print, message = is_print_only(code, language)
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
            if os.name == "nt":
                filepath = f"{filename}.c"
                exe_file = f"{filename}.exe"
                with open(filepath, "w") as f:
                    f.write(code)
                subprocess.run(["gcc", filepath, "-o", exe_file], timeout=5)
                cmd = [exe_file]
                files_to_delete.extend([filepath, exe_file])
            elif os.name == "posix":
                filepath = f"{filename}.c"
                exe_file = f"./{filename}"  # Linux executable without .exe, prefixed with ./
                with open(filepath, "w") as f:
                    f.write(code)
                subprocess.run(["gcc", filepath, "-o", exe_file], timeout=5)
                cmd = [exe_file]
                files_to_delete.extend([filepath, exe_file])

        elif language == "java":
            # Use capitalized class name and filename
            class_name = "Main"
            java_file = f"{class_name}.java"
            with open(java_file, "w") as f:
                f.write(f"public class {class_name} {{\n{code}\n}}")
            compile_proc = subprocess.run(["javac", java_file], capture_output=True, text=True, timeout=5)
            if compile_proc.returncode != 0:
                return {"stdout": "", "stderr": compile_proc.stderr, "success": False}
            cmd = ["java", class_name]
            files_to_delete.extend([java_file, f"{class_name}.class"])

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
            else:
                print(f"File to delete not found: {f}")
