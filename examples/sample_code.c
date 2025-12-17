/**
 * 示例代码 - 用于测试模糊测试驱动生成
 * 包含一些常见的漏洞模式
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/**
 * 解析整数字符串
 * @param str 输入字符串
 * @return 解析后的整数
 */
int parse_int(const char *str) {
    if (str == NULL) {
        return 0;
    }
    return atoi(str);
}

/**
 * 复制字符串到缓冲区
 * 潜在的缓冲区溢出漏洞
 */
void copy_string(char *dest, const char *src, size_t dest_size) {
    if (dest == NULL || src == NULL) {
        return;
    }
    // 危险: 没有检查长度
    strcpy(dest, src);
}

/**
 * 安全的字符串复制
 */
void safe_copy_string(char *dest, const char *src, size_t dest_size) {
    if (dest == NULL || src == NULL || dest_size == 0) {
        return;
    }
    strncpy(dest, src, dest_size - 1);
    dest[dest_size - 1] = '\0';
}

/**
 * 处理用户输入
 * @param input 用户输入数据
 * @param len 数据长度
 * @return 处理结果
 */
int process_input(const unsigned char *input, size_t len) {
    if (input == NULL || len == 0) {
        return -1;
    }
    
    // 检查魔数
    if (len >= 4 && input[0] == 'F' && input[1] == 'U' && 
        input[2] == 'Z' && input[3] == 'Z') {
        
        // 解析长度字段
        if (len >= 8) {
            size_t data_len = *(size_t*)(input + 4);
            
            // 潜在的整数溢出
            if (data_len > 0 && len >= 8 + data_len) {
                char *buffer = malloc(data_len);
                if (buffer) {
                    memcpy(buffer, input + 8, data_len);
                    // 处理数据...
                    free(buffer);
                    return 0;
                }
            }
        }
    }
    
    return 1;
}

/**
 * 计算数组元素之和
 */
long sum_array(const int *arr, size_t count) {
    if (arr == NULL) {
        return 0;
    }
    
    long sum = 0;
    for (size_t i = 0; i < count; i++) {
        sum += arr[i];
    }
    return sum;
}

/**
 * 查找字符串中的子串
 */
const char* find_substring(const char *haystack, const char *needle) {
    if (haystack == NULL || needle == NULL) {
        return NULL;
    }
    return strstr(haystack, needle);
}
