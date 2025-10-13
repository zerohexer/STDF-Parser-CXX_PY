#!/usr/bin/env python3
"""
Universal script to add a new STDF record type.
Works on Windows, Linux, and macOS.

Usage:
    python scripts/add_record_type.py TSR rec_tsr 10 30
    python scripts/add_record_type.py WIR rec_wir 2 10

This script automatically generates:
1. Entry in cpp/field_defs/record_types.def
2. Template declaration in cpp/include/dynamic_field_extractor.h
3. Template implementation in cpp/src/dynamic_field_extractor.cpp
4. Placeholder field definition file cpp/field_defs/XXX_fields.def
"""

import sys
import os
import re
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

    @staticmethod
    def disable():
        """Disable colors (for Windows cmd without ANSI support)."""
        Colors.RED = ''
        Colors.GREEN = ''
        Colors.YELLOW = ''
        Colors.BLUE = ''
        Colors.MAGENTA = ''
        Colors.CYAN = ''
        Colors.RESET = ''
        Colors.BOLD = ''


# Detect Windows and enable ANSI colors
if sys.platform == 'win32':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except:
        Colors.disable()


def print_header(text):
    """Print formatted header."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 60}{Colors.RESET}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {text}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {text}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {text}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {text}")


def find_project_root():
    """Find the project root directory (contains cpp/ folder)."""
    current = Path.cwd()

    # Try current directory first
    if (current / 'cpp' / 'field_defs').exists():
        return current

    # Try parent directories
    for parent in current.parents:
        if (parent / 'cpp' / 'field_defs').exists():
            return parent

    print_error("Could not find project root (cpp/field_defs not found)")
    print_info("Please run this script from the project root directory")
    sys.exit(1)


def check_record_exists(root, record_name):
    """Check if record type already exists in registry."""
    registry_file = root / 'cpp' / 'field_defs' / 'record_types.def'

    if not registry_file.exists():
        return False

    with open(registry_file, 'r') as f:
        content = f.read()

    # Check if RECORD_TYPE(NAME, ...) exists (but ignore commented lines)
    # Pattern: Line must NOT start with // (after optional whitespace)
    pattern = rf'^\s*(?!//)\s*RECORD_TYPE\({record_name}\s*,'
    return re.search(pattern, content, re.MULTILINE) is not None


def add_to_registry(root, record_name, struct_name, rec_typ, rec_sub):
    """Add record type to cpp/field_defs/record_types.def."""
    registry_file = root / 'cpp' / 'field_defs' / 'record_types.def'

    if not registry_file.exists():
        print_error(f"Registry file not found: {registry_file}")
        return False

    # Read current content
    with open(registry_file, 'r') as f:
        lines = f.readlines()

    # Find the last RECORD_TYPE line
    last_record_line = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('RECORD_TYPE('):
            last_record_line = i

    if last_record_line == -1:
        print_error("Could not find any RECORD_TYPE entries in registry")
        return False

    # Create new entry
    macro_name = f"REC_{record_name}"
    new_entry = f"RECORD_TYPE({record_name}, {struct_name}, {rec_typ}, {rec_sub}, {macro_name})  // {record_name} Record\n"

    # Insert after last RECORD_TYPE
    lines.insert(last_record_line + 1, new_entry)

    # Write back
    with open(registry_file, 'w') as f:
        f.writelines(lines)

    print_success(f"Added {record_name} to registry: {registry_file}")
    return True


def add_template_declaration(root, record_name, struct_name):
    """Add template declaration to cpp/include/dynamic_field_extractor.h."""
    header_file = root / 'cpp' / 'include' / 'dynamic_field_extractor.h'

    if not header_file.exists():
        print_error(f"Header file not found: {header_file}")
        return False

    # Read current content
    with open(header_file, 'r') as f:
        content = f.read()

    # Check if already exists
    if f"extract_fields<{struct_name}>" in content:
        print_warning(f"Template declaration for {struct_name} already exists in header")
        return True

    # Find the last template specialization declaration
    pattern = r'template<>\s+void\s+DynamicFieldExtractor::extract_fields<\w+>'
    matches = list(re.finditer(pattern, content))

    if not matches:
        print_error("Could not find template declarations in header")
        return False

    last_match = matches[-1]
    insertion_point = last_match.end()

    # Find the end of that line
    newline_pos = content.find('\n', insertion_point)
    if newline_pos == -1:
        newline_pos = len(content)

    # Create new declaration
    new_declaration = f"\ntemplate<> void DynamicFieldExtractor::extract_fields<{struct_name}>({struct_name}* record, DynamicSTDFRecord& out_record);"

    # Insert
    new_content = content[:newline_pos + 1] + new_declaration + content[newline_pos + 1:]

    # Write back
    with open(header_file, 'w') as f:
        f.write(new_content)

    print_success(f"Added template declaration to: {header_file}")
    return True


def add_template_implementation(root, record_name, struct_name):
    """Add template implementation to cpp/src/dynamic_field_extractor.cpp."""
    impl_file = root / 'cpp' / 'src' / 'dynamic_field_extractor.cpp'

    if not impl_file.exists():
        print_error(f"Implementation file not found: {impl_file}")
        return False

    # Read current content
    with open(impl_file, 'r') as f:
        content = f.read()

    # Check if already exists
    if f"extract_fields<{struct_name}>" in content:
        print_warning(f"Template implementation for {struct_name} already exists")
        return True

    # Find the last template specialization - use simpler pattern to find start
    pattern = r'template<>\s*\n\s*void\s+DynamicFieldExtractor::extract_fields<\w+>'
    matches = list(re.finditer(pattern, content))

    if not matches:
        print_error("Could not find template implementations")
        return False

    last_match = matches[-1]

    # Now find the closing brace of this function using brace counting
    search_start = last_match.end()
    brace_count = 0
    found_opening = False
    closing_pos = search_start

    for i in range(search_start, len(content)):
        if content[i] == '{':
            brace_count += 1
            found_opening = True
        elif content[i] == '}':
            brace_count -= 1
            if found_opening and brace_count == 0:
                closing_pos = i + 1
                break

    insertion_point = closing_pos

    # Create new implementation
    field_def_file = f"{record_name.lower()}_fields.def"
    new_implementation = f'''

// {record_name} Record Extraction
template<>
void DynamicFieldExtractor::extract_fields<{struct_name}>({struct_name}* {record_name.lower()}, DynamicSTDFRecord& out_record) {{
    if (!{record_name.lower()}) return;

    out_record.type_name = "{record_name}";
    const std::set<std::string>& enabled = get_enabled_fields("{record_name}");

    if (enabled.empty()) return;

    // X-Macros: Unified field extraction
    #define FIELD(name, member) \\
        if (enabled.count(name)) {{ \\
            out_record.fields[name] = field_to_string({record_name.lower()}->member); \\
        }}

    #include "../field_defs/{field_def_file}"
    #undef FIELD
}}
'''

    # Insert
    new_content = content[:insertion_point] + new_implementation + content[insertion_point:]

    # Write back
    with open(impl_file, 'w') as f:
        f.write(new_content)

    print_success(f"Added template implementation to: {impl_file}")
    return True


def add_to_available_fields(root, record_name):
    """Add to get_all_available_fields() function."""
    impl_file = root / 'cpp' / 'src' / 'dynamic_field_extractor.cpp'

    if not impl_file.exists():
        return False

    # Read current content
    with open(impl_file, 'r') as f:
        content = f.read()

    # Check if already exists
    if f'if (record_type == "{record_name}")' in content:
        print_warning(f"{record_name} already exists in get_all_available_fields()")
        return True

    # Find the get_all_available_fields function
    func_pattern = r'std::set<std::string>\s+DynamicFieldExtractor::get_all_available_fields'
    match = re.search(func_pattern, content)

    if not match:
        print_warning("Could not find get_all_available_fields() function")
        return True  # Not critical, continue

    # Find the last "else if (record_type ==" block
    search_start = match.start()
    pattern = r'else\s+if\s+\(record_type\s+==\s+"(\w+)"\)'
    matches = list(re.finditer(pattern, content[search_start:]))

    if not matches:
        print_warning("Could not find else-if blocks in get_all_available_fields()")
        return True

    last_match = matches[-1]

    # Find the closing brace of that block
    block_start = search_start + last_match.end()
    brace_count = 0
    found_opening = False
    closing_pos = block_start

    for i in range(block_start, len(content)):
        if content[i] == '{':
            brace_count += 1
            found_opening = True
        elif content[i] == '}':
            brace_count -= 1
            if found_opening and brace_count == 0:
                closing_pos = i + 1
                break

    # Create new else-if block
    field_def_file = f"{record_name.lower()}_fields.def"
    new_block = f'''
    else if (record_type == "{record_name}") {{
        #define FIELD(name, member) available_fields.insert(name);
        #include "../field_defs/{field_def_file}"
        #undef FIELD
    }}'''

    # Insert
    new_content = content[:closing_pos] + new_block + content[closing_pos:]

    # Write back
    with open(impl_file, 'w') as f:
        f.write(new_content)

    print_success(f"Added {record_name} to get_all_available_fields()")
    return True


def create_field_definition(root, record_name, struct_name):
    """Create placeholder field definition file."""
    field_def_file = root / 'cpp' / 'field_defs' / f'{record_name.lower()}_fields.def'

    if field_def_file.exists():
        print_warning(f"Field definition file already exists: {field_def_file}")
        return True

    # Create placeholder content with common fields
    content = f'''// {record_name} ({struct_name}) Field Definitions
// Format: FIELD("field_name", struct_member)
//
// TODO: Add actual {record_name} fields from libstdf {struct_name} structure
// Refer to: cpp/third_party/include/libstdf_types.h
//
// Common fields (example):
FIELD("HEAD_NUM", HEAD_NUM)
FIELD("SITE_NUM", SITE_NUM)
FIELD("TEST_NUM", TEST_NUM)

// TODO: Add more fields specific to {record_name} record type
// Examples:
// FIELD("FIELD_NAME", STRUCT_MEMBER)
// FIELD("TEST_TXT", TEST_TXT)
// FIELD("ALARM_ID", ALARM_ID)
'''

    with open(field_def_file, 'w') as f:
        f.write(content)

    print_success(f"Created field definition file: {field_def_file}")
    print_info(f"Please edit {field_def_file} and add actual fields from {struct_name}")
    return True


def print_next_steps(record_name, struct_name):
    """Print next steps for the user."""
    print_header("Next Steps")

    print(f"{Colors.YELLOW}1. Edit Field Definitions{Colors.RESET}")
    print(f"   File: cpp/field_defs/{record_name.lower()}_fields.def")
    print(f"   Action: Add actual fields from libstdf {struct_name} structure")
    print(f"   Reference: cpp/third_party/include/libstdf_types.h")

    print(f"\n{Colors.YELLOW}2. Verify Changes{Colors.RESET}")
    print(f"   Check: cpp/field_defs/record_types.def")
    print(f"   Check: cpp/include/dynamic_field_extractor.h")
    print(f"   Check: cpp/src/dynamic_field_extractor.cpp")

    print(f"\n{Colors.YELLOW}3. Build and Test{Colors.RESET}")
    print(f"   $ rm -f cpp/src/*.o python/stdf_parser_cpp.so")
    print(f"   $ python3 setup.py build_ext --inplace")
    print(f"   $ python3 test_hybrid_approach.py")

    print()


def main():
    """Main entry point."""
    if len(sys.argv) != 5:
        print_error("Invalid arguments")
        print(f"\nUsage: python {sys.argv[0]} RECORD_NAME STRUCT_NAME REC_TYP REC_SUB")
        print("\nExamples:")
        print("  python scripts/add_record_type.py TSR rec_tsr 10 30")
        print("  python scripts/add_record_type.py WIR rec_wir 2 10")
        print("  python scripts/add_record_type.py WRR rec_wrr 2 20")
        sys.exit(1)

    record_name = sys.argv[1].upper()
    struct_name = sys.argv[2]
    rec_typ = sys.argv[3]
    rec_sub = sys.argv[4]

    print_header(f"Adding STDF Record Type: {record_name}")

    print_info(f"Record Name: {record_name}")
    print_info(f"Struct Name: {struct_name}")
    print_info(f"REC_TYP: {rec_typ}")
    print_info(f"REC_SUB: {rec_sub}")

    # Find project root
    root = find_project_root()
    print_info(f"Project Root: {root}")

    # Check if already exists
    print()
    record_exists = check_record_exists(root, record_name)

    if record_exists:
        print_warning(f"{record_name} already exists in registry")
        print_info("This will UPDATE existing files:")
    else:
        print_success(f"{record_name} is a new record type")
        print_info("This will CREATE new files:")

    print(f"  - cpp/field_defs/record_types.def")
    print(f"  - cpp/include/dynamic_field_extractor.h")
    print(f"  - cpp/src/dynamic_field_extractor.cpp")
    print(f"  - cpp/field_defs/{record_name.lower()}_fields.def")

    response = input(f"\n{Colors.YELLOW}Continue? (y/N):{Colors.RESET} ")
    if response.lower() != 'y':
        print_info("Aborted - no files were modified")
        sys.exit(0)

    print()

    # Step 1: Add to registry
    print(f"{Colors.BOLD}Step 1/5: Adding to record_types.def...{Colors.RESET}")
    if not add_to_registry(root, record_name, struct_name, rec_typ, rec_sub):
        sys.exit(1)

    # Step 2: Add template declaration
    print(f"\n{Colors.BOLD}Step 2/5: Adding template declaration...{Colors.RESET}")
    if not add_template_declaration(root, record_name, struct_name):
        sys.exit(1)

    # Step 3: Add template implementation
    print(f"\n{Colors.BOLD}Step 3/5: Adding template implementation...{Colors.RESET}")
    if not add_template_implementation(root, record_name, struct_name):
        sys.exit(1)

    # Step 4: Add to get_all_available_fields
    print(f"\n{Colors.BOLD}Step 4/5: Adding to get_all_available_fields()...{Colors.RESET}")
    add_to_available_fields(root, record_name)

    # Step 5: Create field definition file
    print(f"\n{Colors.BOLD}Step 5/5: Creating field definition file...{Colors.RESET}")
    if not create_field_definition(root, record_name, struct_name):
        sys.exit(1)

    print_header("Success!")
    print_success(f"{record_name} record type has been added successfully!")

    print_next_steps(record_name, struct_name)


if __name__ == '__main__':
    main()
