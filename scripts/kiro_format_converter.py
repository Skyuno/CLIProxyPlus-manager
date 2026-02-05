#!/usr/bin/env python3
"""
Kiro JSON格式互转脚本

支持两种格式之间的互转：
- aiclient2api格式 (驼峰命名)
- cliprproxyplus格式 (下划线命名)
"""

import argparse
import json
import sys
from pathlib import Path


# 字段映射关系：aiclient2api -> cliprproxyplus
FIELD_MAPPING = {
    "accessToken": "access_token",
    "refreshToken": "refresh_token",
    "expiresAt": "expires_at",
    "authMethod": "auth_method",
    "clientId": "client_id",
    "clientSecret": "client_secret",
    "idcRegion": "region",
    "lastRefreshed": "last_refresh",
}

# 反向映射：cliprproxyplus -> aiclient2api
REVERSE_FIELD_MAPPING = {v: k for k, v in FIELD_MAPPING.items()}

# authMethod值映射
AUTH_METHOD_TO_CLIPROXY = {
    "IdC": "idc",
    "Social": "social",
}

AUTH_METHOD_TO_AICLIENT = {v: k for k, v in AUTH_METHOD_TO_CLIPROXY.items()}

# cliprproxyplus格式的默认字段（aiclient2api中不存在的）
CLIPROXY_DEFAULTS = {
    "disabled": False,
    "email": "",
    "profile_arn": "",
    "provider": "AWS",
    "type": "kiro",
}


def aiclient_to_cliproxy(data: dict) -> dict:
    """
    将aiclient2api格式转换为cliprproxyplus格式
    """
    result = {}
    
    for aiclient_key, cliproxy_key in FIELD_MAPPING.items():
        if aiclient_key in data:
            value = data[aiclient_key]
            # 特殊处理authMethod
            if aiclient_key == "authMethod":
                value = AUTH_METHOD_TO_CLIPROXY.get(value, value.lower())
            result[cliproxy_key] = value
    
    # 添加cliprproxyplus格式的默认字段
    for key, default_value in CLIPROXY_DEFAULTS.items():
        if key not in result:
            result[key] = default_value
    
    return result


def cliproxy_to_aiclient(data: dict) -> dict:
    """
    将cliprproxyplus格式转换为aiclient2api格式
    """
    result = {}
    
    for cliproxy_key, aiclient_key in REVERSE_FIELD_MAPPING.items():
        if cliproxy_key in data:
            value = data[cliproxy_key]
            # 特殊处理auth_method
            if cliproxy_key == "auth_method":
                value = AUTH_METHOD_TO_AICLIENT.get(value, value.capitalize())
            result[aiclient_key] = value
    
    return result


def detect_format(data: dict) -> str:
    """
    自动检测JSON格式类型
    返回 'aiclient' 或 'cliproxy' 或 'unknown'
    """
    if "accessToken" in data or "authMethod" in data:
        return "aiclient"
    elif "access_token" in data or "auth_method" in data:
        return "cliproxy"
    return "unknown"


def convert_file(input_path: Path, output_path: Path | None, target_format: str | None) -> dict:
    """
    转换文件格式
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径（可选，默认为标准输出）
        target_format: 目标格式 'aiclient' 或 'cliproxy'（可选，自动检测并转换）
    
    Returns:
        转换后的数据
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    source_format = detect_format(data)
    
    if source_format == "unknown":
        raise ValueError(f"无法识别输入文件的格式: {input_path}")
    
    # 确定目标格式
    if target_format is None:
        target_format = "cliproxy" if source_format == "aiclient" else "aiclient"
    
    # 如果源格式和目标格式相同，直接返回
    if source_format == target_format:
        print(f"输入文件已经是{target_format}格式，无需转换", file=sys.stderr)
        return data
    
    # 执行转换
    if target_format == "cliproxy":
        result = aiclient_to_cliproxy(data)
    else:
        result = cliproxy_to_aiclient(data)
    
    # 输出结果
    output_json = json.dumps(result, indent=2, ensure_ascii=False)
    
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
            f.write("\n")
        print(f"转换完成: {input_path} -> {output_path}", file=sys.stderr)
    else:
        print(output_json)
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Kiro JSON格式互转工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 自动检测并转换（aiclient2api -> cliprproxyplus 或反之）
  python kiro_format_converter.py input.json
  
  # 指定输出文件
  python kiro_format_converter.py input.json -o output.json
  
  # 强制转换为cliprproxyplus格式
  python kiro_format_converter.py input.json --to cliproxy
  
  # 强制转换为aiclient2api格式
  python kiro_format_converter.py input.json --to aiclient
        """
    )
    
    parser.add_argument(
        "input",
        type=Path,
        help="输入JSON文件路径"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="输出JSON文件路径（默认输出到标准输出）"
    )
    
    parser.add_argument(
        "--to",
        choices=["aiclient", "cliproxy"],
        default=None,
        help="目标格式（默认自动检测并转换为另一种格式）"
    )
    
    args = parser.parse_args()
    
    if not args.input.exists():
        print(f"错误: 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    try:
        convert_file(args.input, args.output, args.to)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
