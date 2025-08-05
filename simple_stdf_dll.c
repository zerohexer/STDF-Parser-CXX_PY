/* Simple STDF DLL for Windows - No external dependencies */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

// Simple STDF record structure
typedef struct {
    unsigned char type;
    unsigned char subtype;
    unsigned short length;
    unsigned int test_num;
    char data[256];
} SimpleSTDFRecord;

// Export functions for DLL
__declspec(dllexport) void* simple_stdf_open(const char* filename) {
    FILE* file = fopen(filename, "rb");
    return (void*)file;
}

__declspec(dllexport) int simple_stdf_read_record(void* file_handle, SimpleSTDFRecord* record) {
    FILE* file = (FILE*)file_handle;
    if (!file || !record) return 0;
    
    // Read basic STDF header (4 bytes: length, type, subtype)
    unsigned char header[4];
    if (fread(header, 1, 4, file) != 4) {
        return 0; // EOF or error
    }
    
    record->length = (header[1] << 8) | header[0];  // Little-endian length
    record->type = header[2];
    record->subtype = header[3];
    record->test_num = 0;
    
    // Skip the record data (simplified parsing)
    if (record->length > 0) {
        fseek(file, record->length, SEEK_CUR);
    }
    
    return 1; // Success
}

__declspec(dllexport) void simple_stdf_close(void* file_handle) {
    FILE* file = (FILE*)file_handle;
    if (file) {
        fclose(file);
    }
}

__declspec(dllexport) const char* simple_stdf_version(void) {
    return "Simple STDF DLL v1.0 - Native Windows";
}

// DLL entry point
BOOL APIENTRY DllMain(HMODULE hModule, DWORD dwReason, LPVOID lpReserved) {
    return TRUE;
}