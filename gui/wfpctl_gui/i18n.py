from __future__ import annotations

import json
import os

EN = "en"
ZH = "zh"

_TR: dict[str, dict[str, str]] = {
    EN: {
        "app_title": "wfpctl - Windows Firewall Console (Administrator)",
        "file": "File",
        "rules": "Rules",
        "tools": "Tools",
        "help": "Help",
        "language": "Language",
        "refresh_rules": "Refresh Rules",
        "export_rules": "Export Rules...",
        "import_rules": "Import Rules...",
        "quit": "Exit",
        "add_block_rule": "Add Block Rule",
        "add_allow_rule": "Add Allow Rule",
        "delete_selected": "Delete Selected",
        "view_sublayers": "View Sublayers",
        "clear_all_rules": "Clear All Rules",
        "about": "About",
        "toolbar": "Toolbar",
        "col_id": "ID",
        "col_name": "Name",
        "col_dir": "Dir",
        "col_action": "Action",
        "col_layer": "Layer",
        "col_sublayer": "Sublayer",
        "col_weight": "Weight",
        "col_guid": "GUID",
        "filter_only": "Only wfpctl rules",
        "filter_all": "All sublayers",
        "filter_tip": "Filter rules by sublayer",
        "lang_english": "English",
        "lang_chinese": "Chinese",
        "layer_out4": "Out V4",
        "layer_out6": "Out V6",
        "layer_in4": "In V4",
        "layer_in6": "In V6",
        "layer_conn_redir4": "ConnRedirect V4",
        "layer_conn_redir6": "ConnRedirect V6",
        "layer_recv_redir4": "RecvRedirect V4",
        "layer_recv_redir6": "RecvRedirect V6",
        "layer_out_tran4": "OutTran V4",
        "layer_out_tran6": "OutTran V6",
        "layer_in_tran4": "InTran V4",
        "layer_in_tran6": "InTran V6",
        "layer_out_ip4": "OutPkt V4",
        "layer_out_ip6": "OutPkt V6",
        "layer_in_ip4": "InPkt V4",
        "layer_in_ip6": "InPkt V6",
        "layer_stream4": "Stream V4",
        "layer_stream6": "Stream V6",
        "layer_flow4": "Flow V4",
        "layer_flow6": "Flow V6",
        "all_layers_label": "Apply to all relevant layers (redirect/transport/IP/stream/flow)",
        "eng_not_found": "Engine Not Found",
        "eng_not_found_msg": "wfpctl executable not found.\nMake sure wfpctl.exe is in the program directory or on PATH.",
        "status_rules": "Rules: {n}",
        "export_title": "Export Rules",
        "export_filter": "Rule files (*.json);;All files (*)",
        "export_done_title": "Export Complete",
        "export_done_msg": "Exported {count} rules to:\n{path}",
        "export_status": "Exported {count} rules",
        "export_fail_title": "Export Failed",
        "import_title": "Import Rules",
        "import_done_title": "Import Complete",
        "import_added": "Added: {n}",
        "import_skipped": "Skipped (already exists): {n}",
        "import_failed": "Failed: {n}",
        "error_details": "Error details:",
        "import_fail_title": "Import Failed",
        "op_success_title": "Success",
        "op_fail_title": "Failed",
        "confirm_delete_title": "Confirm Delete",
        "confirm_delete_msg": "Delete the selected {n} rule(s)?",
        "delete_error_title": "Delete Error",
        "deleted_status": "Deleted selected rules",
        "sublayer_info": "Sublayer Info",
        "del_sublayer_btn": "  Delete Selected Sublayer",
        "close_btn": "  Close",
        "confirm_delete_sub_title": "Confirm Delete",
        "confirm_delete_sub_msg": "Delete the selected {n} sublayer(s)?\nThis removes all rules in those sublayers.",
        "delete_fail_title": "Delete Failed",
        "confirm_cleanup_title": "Confirm Cleanup",
        "confirm_cleanup_msg": "Clear all rules?\nThis removes wfpctl's sublayer, provider and all rules.",
        "cleanup_done_title": "Cleanup Complete",
        "cleanup_fail_title": "Cleanup Failed",
        "copy_guid": "Copy GUID",
        "refresh_ctx": "Refresh",
        "copied_guid": "Copied GUID",
        "about_title": "About wfpctl",
        "about_main_title": "wfpctl - Windows Firewall Console",
        "engine_ver": "Engine version: {ver}",
        "add_rule_title": "Add Rule",
        "rule_name_label": "Rule name:",
        "target_label": "Target IP/CIDR:",
        "target_ph": "e.g. 192.168.1.0/24",
        "port_label": "Port/Range:",
        "port_ph": "e.g. 80 or 80-443",
        "protocol_label": "Protocol:",
        "proto_any": "(Any)",
        "direction_label": "Direction:",
        "dir_out": "Out",
        "dir_in": "In",
        "action_label": "Action:",
        "act_block": "Block",
        "act_allow": "Allow",
        "priority_label": "Priority:",
        "prio_highest": "Highest",
        "prio_lowest": "Lowest",
        "prio_custom": "Custom",
        "weight_label": "Custom weight:",
        "validate_title": "Validation Error",
        "target_required": "Target IP/CIDR must not be empty",
        "timeout_msg": "Command timed out: {cmd}",
        "exec_fail_msg": "Execution failed: {err}",
        "not_rules_file": "Not a wfpctl rules file",
        "missing_rules_list": "Missing rules list in rule file",
        "invalid_record": "Rule {i}: invalid record format",
        "record_error": "Rule {i}: {msg}",
        "exit_code": "exit code {rc}",
    },
    ZH: {
        "app_title": "wfpctl - Windows 防火墙控制台 (管理员)",
        "file": "文件",
        "rules": "规则",
        "tools": "工具",
        "help": "帮助",
        "language": "语言",
        "refresh_rules": "刷新规则",
        "export_rules": "导出规则…",
        "import_rules": "导入规则…",
        "quit": "退出",
        "add_block_rule": "添加阻止规则",
        "add_allow_rule": "添加允许规则",
        "delete_selected": "删除所选",
        "view_sublayers": "查看子层",
        "clear_all_rules": "清理全部规则",
        "about": "关于",
        "toolbar": "工具栏",
        "col_id": "ID",
        "col_name": "名称",
        "col_dir": "方向",
        "col_action": "动作",
        "col_layer": "层",
        "col_sublayer": "子层",
        "col_weight": "权重",
        "col_guid": "GUID",
        "filter_only": "仅 wfpctl 规则",
        "filter_all": "所有子层 (All)",
        "filter_tip": "按子层筛选规则",
        "lang_english": "英语",
        "lang_chinese": "中文",
        "layer_out4": "出站 V4",
        "layer_out6": "出站 V6",
        "layer_in4": "入站 V4",
        "layer_in6": "入站 V6",
        "layer_conn_redir4": "连接重定向 V4",
        "layer_conn_redir6": "连接重定向 V6",
        "layer_recv_redir4": "接收重定向 V4",
        "layer_recv_redir6": "接收重定向 V6",
        "layer_out_tran4": "出站传输 V4",
        "layer_out_tran6": "出站传输 V6",
        "layer_in_tran4": "入站传输 V4",
        "layer_in_tran6": "入站传输 V6",
        "layer_out_ip4": "出站IP包 V4",
        "layer_out_ip6": "出站IP包 V6",
        "layer_in_ip4": "入站IP包 V4",
        "layer_in_ip6": "入站IP包 V6",
        "layer_stream4": "流 V4",
        "layer_stream6": "流 V6",
        "layer_flow4": "流建立 V4",
        "layer_flow6": "流建立 V6",
        "all_layers_label": "应用到所有相关层（重定向/传输/IP包/流/流建立）",
        "eng_not_found": "引擎未找到",
        "eng_not_found_msg": "未找到 wfpctl 可执行文件。\n请确保 wfpctl.exe 在程序目录或 PATH 中。",
        "status_rules": "规则数: {n}",
        "export_title": "导出规则",
        "export_filter": "规则文件 (*.json);;所有文件 (*)",
        "export_done_title": "导出完成",
        "export_done_msg": "已导出 {count} 条规则到:\n{path}",
        "export_status": "已导出 {count} 条规则",
        "export_fail_title": "导出失败",
        "import_title": "导入规则",
        "import_done_title": "导入完成",
        "import_added": "新增: {n}",
        "import_skipped": "跳过(已存在): {n}",
        "import_failed": "失败: {n}",
        "error_details": "错误详情:",
        "import_fail_title": "导入失败",
        "op_success_title": "操作成功",
        "op_fail_title": "操作失败",
        "confirm_delete_title": "确认删除",
        "confirm_delete_msg": "确定要删除选中的 {n} 条规则吗？",
        "delete_error_title": "删除错误",
        "deleted_status": "已删除所选规则",
        "sublayer_info": "子层信息",
        "del_sublayer_btn": " 删除选中子层",
        "close_btn": " 关闭",
        "confirm_delete_sub_title": "确认删除",
        "confirm_delete_sub_msg": "确定要删除选中的 {n} 个子层吗？\n这将移除子层中的所有规则。",
        "delete_fail_title": "删除失败",
        "confirm_cleanup_title": "确认清理",
        "confirm_cleanup_msg": "确定要清理全部规则吗？\n这将移除 wfpctl 的子层、提供者和所有规则。",
        "cleanup_done_title": "清理完成",
        "cleanup_fail_title": "清理失败",
        "copy_guid": "复制 GUID",
        "refresh_ctx": "刷新",
        "copied_guid": "已复制 GUID",
        "about_title": "关于 wfpctl",
        "about_main_title": "wfpctl - Windows 防火墙控制台",
        "engine_ver": "引擎版本: {ver}",
        "add_rule_title": "添加规则",
        "rule_name_label": "规则名称:",
        "target_label": "目标 IP/CIDR:",
        "target_ph": "例如 192.168.1.0/24",
        "port_label": "端口/区间:",
        "port_ph": "例如 80 或 80-443",
        "protocol_label": "协议:",
        "proto_any": "(任一)",
        "direction_label": "方向:",
        "dir_out": "出站",
        "dir_in": "入站",
        "action_label": "动作:",
        "act_block": "阻止",
        "act_allow": "允许",
        "priority_label": "优先级:",
        "prio_highest": "最高",
        "prio_lowest": "最低",
        "prio_custom": "自定义",
        "weight_label": "自定义权重:",
        "validate_title": "验证错误",
        "target_required": "目标 IP/CIDR 不能为空",
        "timeout_msg": "命令超时: {cmd}",
        "exec_fail_msg": "执行失败: {err}",
        "not_rules_file": "不是 wfpctl 规则文件",
        "missing_rules_list": "规则文件中缺少 rules 列表",
        "invalid_record": "第 {i} 条: 记录格式无效",
        "record_error": "第 {i} 条: {msg}",
        "exit_code": "退出码 {rc}",
    },
}

_DEFAULT_LANG = EN
_current = EN


def set_language(lang: str) -> None:
    global _current
    _current = lang if lang in _TR else EN


def current_language() -> str:
    return _current


def tr(key: str) -> str:
    return _TR[_current].get(key, key)


def lang_name(lang: str) -> str:
    return {
        EN: tr("lang_english"),
        ZH: tr("lang_chinese"),
    }.get(lang, lang)


def settings_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "wfpctl", "gui.json")


def load_language() -> str:
    try:
        with open(settings_path(), "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        lang = doc.get("language", "")
        if lang in _TR:
            return lang
    except Exception:
        pass
    return _DEFAULT_LANG


def save_language(lang: str) -> None:
    try:
        path = settings_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"language": lang}, fh)
    except Exception:
        pass