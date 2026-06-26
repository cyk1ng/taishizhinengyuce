"""
排班调度模块 - 基于 OC_SCHEDULE_TEAM / OC_SCHEDULE_RECORD 两张 Oracle 表

核心功能：
  1. 获取班组人员信息 (OC_SCHEDULE_TEAM)
  2. 获取现有排班记录 (OC_SCHEDULE_RECORD)
  3. 智能排班生成
  4. 排班公平性分析
  5. 排班报表导出
  6. 根据 ON_DUTY_TIME 自动识别班次类型（早/中/晚）
"""

import json
import csv
import io
import os
from datetime import datetime, date, timedelta, time
from typing import Optional, Any
from dataclasses import dataclass, field, asdict

from langchain.tools import tool
from coze_coding_utils.runtime_ctx.context import new_context
from coze_coding_utils.log.write_log import request_context

# ═══════════════════════════════════════════════
#  数据模型 — 严格对齐 OC_SCHEDULE_TEAM
# ═══════════════════════════════════════════════

@dataclass
class OcScheduleTeam:
    """OC_SCHEDULE_TEAM 班组表"""
    team_id: str = ""
    team_name: str = ""
    team_leader_id: str = ""
    team_leader_name: str = ""
    create_busi_dept_id: str = ""
    create_busi_dept_name: str = ""
    enable_flag: str = "Y"
    other_person_ids: str = ""     # 逗号分隔
    other_person_names: str = ""   # 逗号分隔

    @property
    def person_id_list(self) -> list[str]:
        """解析 other_person_ids 为列表"""
        if not self.other_person_ids:
            return []
        return [p.strip() for p in self.other_person_ids.split(",") if p.strip()]

    @property
    def person_name_list(self) -> list[str]:
        """解析 other_person_names 为列表"""
        if not self.other_person_names:
            return []
        return [n.strip() for n in self.other_person_names.split(",") if n.strip()]

    @property
    def all_members(self) -> list[dict]:
        """获取班组完整成员列表（含值班长）"""
        members = []
        if self.team_leader_id and self.team_leader_name:
            members.append({
                "user_id": self.team_leader_id,
                "user_name": self.team_leader_name,
                "role": "值班长"
            })
        ids = self.person_id_list
        names = self.person_name_list
        for i, uid in enumerate(ids):
            name = names[i] if i < len(names) else f"人员{uid}"
            members.append({
                "user_id": uid,
                "user_name": name,
                "role": "值班人员"
            })
        return members


# ═══════════════════════════════════════════════
#  数据模型 — 严格对齐 OC_SCHEDULE_RECORD
# ═══════════════════════════════════════════════

@dataclass
class OcScheduleRecord:
    """OC_SCHEDULE_RECORD 排班记录表"""
    record_id: str = ""
    dis_org_id: str = ""
    dis_org_name: str = ""
    team_id: str = ""
    team_name: str = ""
    schedule_status: str = "Y"         # Y=在值, N=已交班
    change_time: Optional[datetime] = None
    on_duty_time: Optional[datetime] = None
    off_duty_time: Optional[datetime] = None
    team_leader_id: str = ""
    team_leader_name: str = ""
    other_person_ids: str = ""
    other_person_names: str = ""
    # 跨班组临时借调人员（不改变其所属班组）
    temp_person_ids: str = ""
    temp_person_names: str = ""

    @property
    def person_id_list(self) -> list[str]:
        if not self.other_person_ids:
            return []
        return [p.strip() for p in self.other_person_ids.split(",") if p.strip()]

    @property
    def person_name_list(self) -> list[str]:
        if not self.other_person_names:
            return []
        return [n.strip() for n in self.other_person_names.split(",") if n.strip()]

    @property
    def temp_person_id_list(self) -> list[str]:
        """解析临时借调人员 ID"""
        if not self.temp_person_ids:
            return []
        return [p.strip() for p in self.temp_person_ids.split(",") if p.strip()]

    @property
    def temp_person_name_list(self) -> list[str]:
        """解析临时借调人员姓名"""
        if not self.temp_person_names:
            return []
        return [n.strip() for n in self.temp_person_names.split(",") if n.strip()]

    @property
    def all_personnel(self) -> list[dict]:
        """完整排班人员列表（核心成员 + 临时借调人员）"""
        people = []
        # 值班长
        if self.team_leader_id and self.team_leader_name:
            people.append({
                "id": self.team_leader_id,
                "name": self.team_leader_name,
                "role": "值班长",
                "type": "core"
            })
        # 核心值班人员
        ids = self.person_id_list
        names = self.person_name_list
        for i, uid in enumerate(ids):
            name = names[i] if i < len(names) else f"人员{uid}"
            people.append({
                "id": uid,
                "name": name,
                "role": "值班人员",
                "type": "core"
            })
        # 临时借调人员
        temp_ids = self.temp_person_id_list
        temp_names = self.temp_person_name_list
        for i, uid in enumerate(temp_ids):
            name = temp_names[i] if i < len(temp_names) else f"临时人员{uid}"
            people.append({
                "id": uid,
                "name": name,
                "role": "临时值班人员",
                "type": "temp"
            })
        return people

    def add_temp_person(self, person_id: str, person_name: str) -> None:
        """添加临时借调人员"""
        existing_ids = self.temp_person_id_list
        if person_id in existing_ids:
            return  # 已存在，不重复添加
        existing_ids.append(person_id)
        existing_names = self.temp_person_name_list
        existing_names.append(person_name)
        self.temp_person_ids = ",".join(existing_ids)
        self.temp_person_names = ",".join(existing_names)

    def remove_temp_person(self, person_id: str) -> bool:
        """移除临时借调人员，返回是否成功移除"""
        existing_ids = self.temp_person_id_list
        if person_id not in existing_ids:
            return False
        idx = existing_ids.index(person_id)
        existing_names = self.temp_person_name_list
        existing_ids.pop(idx)
        if idx < len(existing_names):
            existing_names.pop(idx)
        self.temp_person_ids = ",".join(existing_ids)
        self.temp_person_names = ",".join(existing_names)
        return True

    def clear_temp_personnel(self) -> int:
        """清空所有临时借调人员，返回清空人数"""
        count = len(self.temp_person_id_list)
        self.temp_person_ids = ""
        self.temp_person_names = ""
        return count

    def end_shift(self) -> dict:
        """
        交班操作：
        1. 设置 schedule_status = 'N'
        2. 记录交班时间
        3. 自动清除临时借调人员
        返回交班摘要
        """
        cleared = self.clear_temp_personnel()
        self.schedule_status = "N"
        self.change_time = datetime.now()
        return {
            "team_name": self.team_name,
            "cleared_temp": cleared,
            "change_time": self.change_time.strftime("%Y-%m-%d %H:%M:%S"),
            "msg": f"{self.team_name}已交班，清除{cleared}名临时借调人员"
        }


# ═══════════════════════════════════════════════
#  班次类型自动识别
# ═══════════════════════════════════════════════

def detect_shift_type(on_duty_time: Optional[datetime]) -> str:
    """
    根据 ON_DUTY_TIME 自动识别班次类型

    规则（按上班时间）：
      - 06:00-11:59  → 早班（08:00-16:00）
      - 12:00-19:59  → 中班（16:00-24:00）
      - 20:00-05:59  → 晚班（00:00-08:00）
    """
    if on_duty_time is None:
        return "未知"
    hour = on_duty_time.hour
    if 6 <= hour < 12:
        return "早班"
    elif 12 <= hour < 20:
        return "中班"
    else:  # 20:00-23:59, 00:00-05:59
        return "晚班"


# ═══════════════════════════════════════════════
#  排班配置
# ═══════════════════════════════════════════════

@dataclass
class ScheduleConfig:
    """排班约束与偏好配置"""
    min_rest_days: int = 1               # 同一人两次排班最小间隔天数
    max_consecutive_shifts: int = 2      # 同一人最多连续班次
    preferred_team_size: int = 4         # 每班推荐人数
    shift_duration_hours: int = 8        # 每班标准时长
    work_start_hour: int = 8             # 默认早班开始时间


@dataclass
class ScheduleConstraints:
    """排班约束条件"""
    start_date: date
    end_date: date
    city_dept_id: str = ""
    city_dept_name: str = ""


def get_all_teams() -> list[dict]:
    """获取所有班组信息（供API使用）"""
    teams = ScheduleDataProvider.get_teams()
    result = []
    for t in teams:
        result.append({
            "team_id": t.team_id,
            "team_name": t.team_name,
            "team_leader_id": t.team_leader_id,
            "team_leader_name": t.team_leader_name,
            "members": [
                {"id": t.team_leader_id, "name": t.team_leader_name, "role": "值班长"}
            ] + [
                {"id": uid, "name": name, "role": "值班人员"}
                for uid, name in zip(t.person_id_list, t.person_name_list)
            ]
        })
    return result


# ═══════════════════════════════════════════════
#  数据提供层 — 模拟 Oracle 查询
# ═══════════════════════════════════════════════

class ScheduleDataProvider:
    """排班数据提供层（模拟 Oracle 的 OC_SCHEDULE_TEAM / OC_SCHEDULE_RECORD）"""

    # 内存中的排班记录存储（用于支持跨班组临时借调的修改操作）
    _record_store: dict[str, OcScheduleRecord] = {}

    @staticmethod
    def _ensure_record_store():
        """确保内存存储已初始化（延迟加载）"""
        if not ScheduleDataProvider._record_store:
            # 生成最近 7 天的排班记录作为初始数据
            today = date.today()
            start = today - timedelta(days=3)
            end = today + timedelta(days=4)
            records = ScheduleDataProvider._generate_mock_records(start, end)
            for r in records:
                ScheduleDataProvider._record_store[r.record_id] = r

    @staticmethod
    def _generate_mock_records(start_date: date, end_date: date) -> list[OcScheduleRecord]:
        """生成模拟排班记录 —— 每天仅一个班组在值，轮转"""
        records: list[OcScheduleRecord] = []
        teams = ScheduleDataProvider._get_mock_teams_data()
        current = start_date
        idx = 0
        while current <= end_date:
            # 每天轮转一个班组在值（按日期索引选班组）
            on_duty_team_idx = current.day % len(teams)
            for i, team in enumerate(teams):
                if current > end_date:
                    break
                is_on_duty = (i == on_duty_team_idx)
                # 早/中/晚三个班次
                for hour_offset in [8, 12, 18]:
                    on_duty = datetime(current.year, current.month, current.day, hour_offset, 0, 0)
                    off_duty = on_duty + timedelta(hours=8)
                    idx += 1
                    records.append(OcScheduleRecord(
                        record_id=f"SR{current.strftime('%Y%m%d')}_{team.team_id}_{hour_offset}",
                        dis_org_id=team.create_busi_dept_id,
                        dis_org_name=team.create_busi_dept_name,
                        team_id=team.team_id,
                        team_name=team.team_name,
                        schedule_status="Y" if is_on_duty else "N",
                        on_duty_time=on_duty,
                        off_duty_time=off_duty,
                        team_leader_id=team.team_leader_id,
                        team_leader_name=team.team_leader_name,
                        other_person_ids=team.other_person_ids,
                        other_person_names=team.other_person_names,
                        temp_person_ids="",
                        temp_person_names="",
                    ))
            current += timedelta(days=1)
        return records

    @staticmethod
    def _get_mock_teams_data() -> list[OcScheduleTeam]:
        """获取模拟班组数据（实际班组人员）"""
        return [
            OcScheduleTeam(
                team_id="T001", team_name="A班",
                team_leader_id="U001", team_leader_name="宗德文",
                create_busi_dept_id="D001", create_busi_dept_name="广州供电局",
                enable_flag="Y",
                other_person_ids="U101,U102,U103,U104,U105,U106,U107,U108,U109,U110",
                other_person_names="王云,晏清阳,杨凡奇,李浩,王玥,何静,李光临,李杰,杨宏敬,龚瑞泉"
            ),
            OcScheduleTeam(
                team_id="T002", team_name="B班",
                team_leader_id="U002", team_leader_name="朱利明",
                create_busi_dept_id="D001", create_busi_dept_name="广州供电局",
                enable_flag="Y",
                other_person_ids="U201,U202,U203,U204,U205,U206",
                other_person_names="张小丽,王海东,马兴源,杨智翔,丁紫笠,康林春"
            ),
            OcScheduleTeam(
                team_id="T003", team_name="C班",
                team_leader_id="U003", team_leader_name="余永胜",
                create_busi_dept_id="D001", create_busi_dept_name="广州供电局",
                enable_flag="Y",
                other_person_ids="U301,U302,U303,U304,U305,U306,U307",
                other_person_names="王品,高恩福,杨志芳,沙成石,王一格,黄佳,耿绍胜"
            ),
            OcScheduleTeam(
                team_id="T004", team_name="D值",
                team_leader_id="U004", team_leader_name="韦于成",
                create_busi_dept_id="D001", create_busi_dept_name="广州供电局",
                enable_flag="Y",
                other_person_ids="U401,U402,U403,U404,U405,U406,U407,U408",
                other_person_names="王梓伟,潘伟,李云川,保文鸿,杨丽丽,陶胜景,张小丽,黄佳"
            ),
            OcScheduleTeam(
                team_id="T005", team_name="E班",
                team_leader_id="U005", team_leader_name="王勇",
                create_busi_dept_id="D001", create_busi_dept_name="广州供电局",
                enable_flag="Y",
                other_person_ids="U501,U502,U503,U504,U505,U506",
                other_person_names="欧钰慷,李燚,孙裕华,张梅,黑晓捷,宋静"
            ),
            OcScheduleTeam(
                team_id="T006", team_name="乙班",
                team_leader_id="U006", team_leader_name="崔娇",
                create_busi_dept_id="D001", create_busi_dept_name="广州供电局",
                enable_flag="Y",
                other_person_ids="U601,U602",
                other_person_names="桑江艳,王英子"
            ),
            OcScheduleTeam(
                team_id="T007", team_name="甲班",
                team_leader_id="U007", team_leader_name="苏冀",
                create_busi_dept_id="D001", create_busi_dept_name="广州供电局",
                enable_flag="Y",
                other_person_ids="U701,U702",
                other_person_names="张瑞颖,桑江艳"
            ),
        ]

    @staticmethod
    def get_teams(city_dept_id: str = "") -> list[OcScheduleTeam]:
        """
        获取班组信息 — 对应 SELECT * FROM OC_SCHEDULE_TEAM WHERE ENABLE_FLAG='Y'
        """
        teams = ScheduleDataProvider._get_mock_teams_data()
        if city_dept_id:
            teams = [t for t in teams if t.create_busi_dept_id == city_dept_id]
        return teams

    @staticmethod
    def get_records(
        start_date: date,
        end_date: date,
        city_dept_id: str = ""
    ) -> list[OcScheduleRecord]:
        """
        获取排班记录 — 从内存存储中查询
        """
        ScheduleDataProvider._ensure_record_store()
        result = []
        for rec in ScheduleDataProvider._record_store.values():
            if rec.on_duty_time and start_date <= rec.on_duty_time.date() <= end_date:
                if not city_dept_id or rec.dis_org_id == city_dept_id:
                    result.append(rec)
        # 按时间排序
        result.sort(key=lambda r: (r.on_duty_time or datetime.min, r.team_name or ""))
        return result

    @staticmethod
    def get_current_on_duty(city_dept_id: str = "") -> list[OcScheduleRecord]:
        """获取当前正在值勤的排班记录（SCHEDULE_STATUS='Y'）"""
        today = date.today()
        return ScheduleDataProvider.get_records(today, today, city_dept_id)

    @staticmethod
    def get_record_by_id(record_id: str) -> Optional[OcScheduleRecord]:
        """根据 record_id 获取排班记录"""
        ScheduleDataProvider._ensure_record_store()
        return ScheduleDataProvider._record_store.get(record_id)

    @staticmethod
    def update_record(record: OcScheduleRecord) -> bool:
        """更新内存中的排班记录"""
        ScheduleDataProvider._ensure_record_store()
        if record.record_id in ScheduleDataProvider._record_store:
            ScheduleDataProvider._record_store[record.record_id] = record
            return True
        return False

    @staticmethod
    def save_records(records: list[OcScheduleRecord]) -> int:
        """
        保存排班记录 — 写入内存存储
        """
        ScheduleDataProvider._ensure_record_store()
        count = 0
        for rec in records:
            ScheduleDataProvider._record_store[rec.record_id] = rec
            count += 1
        return count

    @staticmethod
    def get_team_by_name(team_name: str) -> Optional[OcScheduleTeam]:
        """根据班组名称查找班组"""
        for t in ScheduleDataProvider._get_mock_teams_data():
            if t.team_name == team_name:
                return t
        return None


# ═══════════════════════════════════════════════
#  智能排班生成器
# ═══════════════════════════════════════════════

class ScheduleGenerator:
    """智能排班生成器"""

    def __init__(self, data_provider: Optional[ScheduleDataProvider] = None):
        self.provider = data_provider or ScheduleDataProvider()
        self.config = ScheduleConfig()

    def can_assign(
        self,
        person_id: str,
        shift_type: str,
        shift_date: date,
        shift_hour: int,
        existing_assignments: dict[str, list[dict]]
    ) -> tuple[bool, str]:
        """检查人员是否可以排入指定班次"""
        assignments = existing_assignments.get(person_id, [])

        # 1. 同一天不能排两个班
        for a in assignments:
            if a["date"] == shift_date:
                return False, f"已在 {shift_date} 安排了 {a['shift']}"

        # 2. 检查最小间隔天数
        for a in assignments:
            diff = abs((shift_date - a["date"]).days)
            if 0 < diff < self.config.min_rest_days:
                return False, f"与上次排班仅间隔 {diff} 天，需要 {self.config.min_rest_days} 天"

        # 3. 检查连续班次上限
        consecutive = 0
        for a in sorted(assignments, key=lambda x: x["date"]):
            if (shift_date - a["date"]).days <= 1:
                consecutive += 1
            else:
                consecutive = 0
        if consecutive >= self.config.max_consecutive_shifts:
            return False, f"连续班次已达上限 {self.config.max_consecutive_shifts}"

        return True, ""

    def generate(
        self,
        constraints: ScheduleConstraints
    ) -> list[OcScheduleRecord]:
        """生成排班计划"""
        teams = self.provider.get_teams(constraints.city_dept_id)
        if not teams:
            return []

        existing_records = self.provider.get_records(
            constraints.start_date,
            constraints.end_date,
            constraints.city_dept_id
        )

        # 构建现有排班映射
        existing_map: dict[str, list[dict]] = {}
        for rec in existing_records:
            shift_type = detect_shift_type(rec.on_duty_time)
            if rec.on_duty_time:
                for pid in rec.person_id_list + ([rec.team_leader_id] if rec.team_leader_id else []):
                    existing_map.setdefault(pid, []).append({
                        "date": rec.on_duty_time.date(),
                        "shift": shift_type,
                        "team": rec.team_name
                    })

        new_records: list[OcScheduleRecord] = []
        current = constraints.start_date
        while current <= constraints.end_date:
            # 每天上午/中/晚三个班次
            for hour_offset in [8, 12, 18]:
                # 轮转班组
                team_idx = (len(new_records)) % len(teams)
                team = teams[team_idx]

                on_duty = datetime(current.year, current.month, current.day, hour_offset, 0, 0)
                off_duty = on_duty + timedelta(hours=8)
                shift_type = detect_shift_type(on_duty)

                record_id = f"SR{current.strftime('%Y%m%d')}_{team.team_id}_{hour_offset}"

                # 每天仅第一个班组在值，其余为已交班
                is_on_duty = (len(new_records) % len(teams) == 0)

                new_records.append(OcScheduleRecord(
                    record_id=record_id,
                    dis_org_id=team.create_busi_dept_id,
                    dis_org_name=team.create_busi_dept_name,
                    team_id=team.team_id,
                    team_name=team.team_name,
                    schedule_status="Y" if is_on_duty else "N",
                    on_duty_time=on_duty,
                    off_duty_time=off_duty,
                    team_leader_id=team.team_leader_id,
                    team_leader_name=team.team_leader_name,
                    other_person_ids=team.other_person_ids,
                    other_person_names=team.other_person_names,
                ))
            current += timedelta(days=1)

        return new_records


# ═══════════════════════════════════════════════
#  报表导出
# ═══════════════════════════════════════════════

def export_schedule_to_csv(records: list[OcScheduleRecord]) -> str:
    """导出排班记录为 CSV 格式"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "日期", "班次", "班组", "值班长", "值班长ID",
        "值班人员", "人员ID", "上班时间", "下班时间", "状态"
    ])
    for rec in records:
        shift_type = detect_shift_type(rec.on_duty_time)
        duty_date = rec.on_duty_time.strftime("%Y-%m-%d") if rec.on_duty_time else ""
        on_time = rec.on_duty_time.strftime("%H:%M") if rec.on_duty_time else ""
        off_time = rec.off_duty_time.strftime("%H:%M") if rec.off_duty_time else ""
        status = "在值" if rec.schedule_status == "Y" else "已交班"
        writer.writerow([
            duty_date, shift_type, rec.team_name,
            rec.team_leader_name, rec.team_leader_id,
            rec.other_person_names, rec.other_person_ids,
            on_time, off_time, status
        ])
    return output.getvalue()


# ═══════════════════════════════════════════════
#  公平性分析
# ═══════════════════════════════════════════════

def analyze_fairness(records: list[OcScheduleRecord]) -> dict:
    """
    分析排班公平性

    返回:
        {
            "total_records": int,
            "teams": { team_name: { shifts: int, avg_hours: float } },
            "balance_score": float (0~100),
            "summary": str
        }
    """
    team_stats: dict[str, dict] = {}
    for rec in records:
        name = rec.team_name
        if name not in team_stats:
            team_stats[name] = {"shifts": 0, "total_hours": 0.0}
        team_stats[name]["shifts"] += 1
        shift_type = detect_shift_type(rec.on_duty_time)
        hours = 8  # 标准8小时
        team_stats[name]["total_hours"] += hours

    result: dict[str, Any] = {
        "total_records": len(records),
        "teams": {},
        "balance_score": 100.0,
        "summary": ""
    }

    if not team_stats:
        result["summary"] = "无排班数据"
        return result

    max_shifts = max(s["shifts"] for s in team_stats.values())
    min_shifts = min(s["shifts"] for s in team_stats.values())
    max_hours = max(s["total_hours"] for s in team_stats.values())
    min_hours = min(s["total_hours"] for s in team_stats.values())

    # 公平性评分 = 100 - 偏差百分比
    shift_diff_pct = ((max_shifts - min_shifts) / max(max_shifts, 1)) * 100 if max_shifts > 0 else 0
    hour_diff_pct = ((max_hours - min_hours) / max(max_hours, 1)) * 100 if max_hours > 0 else 0
    balance_score = max(0, 100 - (shift_diff_pct * 0.6 + hour_diff_pct * 0.4))

    for name, stats in sorted(team_stats.items()):
        avg_hours = round(stats["total_hours"] / max(stats["shifts"], 1), 1)
        result["teams"][name] = {
            "shifts": stats["shifts"],
            "avg_hours": avg_hours
        }

    result["balance_score"] = round(balance_score, 1)
    if balance_score >= 90:
        result["summary"] = f"排班公平性良好（{balance_score}分），各班组班次分布均衡"
    elif balance_score >= 70:
        result["summary"] = f"排班公平性一般（{balance_score}分），建议适当调整班次分配"
    else:
        result["summary"] = f"排班公平性较差（{balance_score}分），需要优化轮换策略"

    return result


# ═══════════════════════════════════════════════
#  工具函数 — 6 个对外暴露接口
# ═══════════════════════════════════════════════

@tool
def get_schedule_staff_info(city_dept_id: str = "") -> str:
    """
    获取排班人员信息
    - 查询 OC_SCHEDULE_TEAM 表获取班组及人员配置
    - 返回各班组的人员组成、角色（值班长/值班人员）
    """
    try:
        teams = ScheduleDataProvider.get_teams(city_dept_id)
        if not teams:
            return json.dumps({"code": 0, "data": [], "msg": "暂无班组数据"}, ensure_ascii=False)
        data = []
        for t in teams:
            members = t.all_members
            data.append({
                "team_id": t.team_id,
                "team_name": t.team_name,
                "member_count": len(members),
                "members": members
            })
        return json.dumps({"code": 0, "data": data}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"code": 1, "error": str(e)}, ensure_ascii=False)


@tool
def get_existing_schedule(
    start_date: str = "",
    end_date: str = "",
    city_dept_id: str = ""
) -> str:
    """
    获取现有排班记录 — 查询 OC_SCHEDULE_RECORD 表
    自动识别早/中/晚班次类型
    """
    try:
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date.today()
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()
        records = ScheduleDataProvider.get_records(s_date, e_date, city_dept_id)
        data = []
        for rec in records:
            shift_type = detect_shift_type(rec.on_duty_time)
            data.append({
                "record_id": rec.record_id,
                "team_id": rec.team_id,
                "team_name": rec.team_name,
                "shift_type": shift_type,
                "schedule_status": "在值" if rec.schedule_status == "Y" else "已交班",
                "on_duty_time": rec.on_duty_time.strftime("%Y-%m-%d %H:%M") if rec.on_duty_time else "",
                "off_duty_time": rec.off_duty_time.strftime("%Y-%m-%d %H:%M") if rec.off_duty_time else "",
                "team_leader": rec.team_leader_name,
                "other_personnel": rec.other_person_names,
            })
        return json.dumps({"code": 0, "data": data}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"code": 1, "error": str(e)}, ensure_ascii=False)


@tool
def generate_intelligent_schedule(
    start_date: str = "",
    end_date: str = "",
    city_dept_id: str = ""
) -> str:
    """
    智能排班生成 — 根据 OC_SCHEDULE_TEAM 班组信息自动生成排班表
    每天自动分配早/中/晚三个班次，轮转班组
    """
    try:
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date.today()
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()

        constraints = ScheduleConstraints(
            start_date=s_date,
            end_date=e_date,
            city_dept_id=city_dept_id
        )
        generator = ScheduleGenerator()
        records = generator.generate(constraints)

        data = []
        for rec in records:
            shift_type = detect_shift_type(rec.on_duty_time)
            data.append({
                "date": rec.on_duty_time.strftime("%Y-%m-%d") if rec.on_duty_time else "",
                "shift": shift_type,
                "team": rec.team_name,
                "team_leader": rec.team_leader_name,
                "members": rec.other_person_names,
                "on_duty": rec.on_duty_time.strftime("%H:%M") if rec.on_duty_time else "",
                "off_duty": rec.off_duty_time.strftime("%H:%M") if rec.off_duty_time else "",
            })
        return json.dumps({"code": 0, "data": data, "total": len(data)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"code": 1, "error": str(e)}, ensure_ascii=False)


@tool
def analyze_schedule_fairness(
    start_date: str = "",
    end_date: str = "",
    city_dept_id: str = ""
) -> str:
    """
    分析排班公平性 — 基于 OC_SCHEDULE_RECORD 历史记录统计各班组班次分布
    """
    try:
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date.today()
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()
        records = ScheduleDataProvider.get_records(s_date, e_date, city_dept_id)
        result = analyze_fairness(records)
        result["code"] = 0
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"code": 1, "error": str(e)}, ensure_ascii=False)


@tool
def export_schedule_report(
    start_date: str = "",
    end_date: str = "",
    city_dept_id: str = ""
) -> str:
    """
    导出排班报表 — 生成 CSV 格式的排班明细
    包含日期、班次、班组、值班长、值班人员、上下班时间
    """
    try:
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date.today()
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()
        records = ScheduleDataProvider.get_records(s_date, e_date, city_dept_id)

        csv_content = export_schedule_to_csv(records)
        filename = f"排班报表_{s_date.strftime('%Y%m%d')}-{e_date.strftime('%Y%m%d')}.csv"

        # 保存到临时目录
        temp_path = os.path.join("/tmp", filename)
        with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(csv_content)

        return json.dumps({
            "code": 0,
            "filename": filename,
            "rows": len(records),
            "content": csv_content,
            "local_path": temp_path
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"code": 1, "error": str(e)}, ensure_ascii=False)


@tool
def save_schedule_records(records_json: str = "") -> str:
    """
    保存排班记录 — 批量写入 OC_SCHEDULE_RECORD 表
    records_json: JSON 格式的排班记录列表
    """
    try:
        records_data = json.loads(records_json) if records_json else []
        if not isinstance(records_data, list):
            records_data = [records_data]

        records: list[OcScheduleRecord] = []
        for item in records_data:
            on_time = datetime.strptime(item.get("on_duty_time", ""), "%Y-%m-%d %H:%M") if item.get("on_duty_time") else None
            off_time = datetime.strptime(item.get("off_duty_time", ""), "%Y-%m-%d %H:%M") if item.get("off_duty_time") else None
            records.append(OcScheduleRecord(
                record_id=item.get("record_id", ""),
                dis_org_id=item.get("dis_org_id", ""),
                dis_org_name=item.get("dis_org_name", ""),
                team_id=item.get("team_id", ""),
                team_name=item.get("team_name", ""),
                schedule_status=item.get("schedule_status", "Y"),
                on_duty_time=on_time,
                off_duty_time=off_time,
                team_leader_id=item.get("team_leader_id", ""),
                team_leader_name=item.get("team_leader_name", ""),
                other_person_ids=item.get("other_person_ids", ""),
                other_person_names=item.get("other_person_names", ""),
                temp_person_ids=item.get("temp_person_ids", ""),
                temp_person_names=item.get("temp_person_names", ""),
            ))

        saved = ScheduleDataProvider.save_records(records)
        return json.dumps({"code": 0, "saved": saved, "msg": f"成功保存 {saved} 条排班记录"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"code": 1, "error": str(e)}, ensure_ascii=False)


# ═══════════════════════════════════════════════
#  跨班组临时借调管理 — 新增 4 个工具
# ═══════════════════════════════════════════════

@tool
def get_staff_detail(team_name: str = "", date_str: str = "") -> str:
    """
    获取值班人员详情 — 返回当值人员和休息人员列表
    - team_name: 班组名称（如 A班, B班），为空则返回所有班组
    - date_str: 日期（YYYY-MM-DD），为空则默认今天
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
        all_teams = ScheduleDataProvider.get_teams()
        records = ScheduleDataProvider.get_records(target_date, target_date)

        # 找出在值的班组
        on_duty_records = [r for r in records if r.schedule_status == "Y"]
        on_duty_team_name = on_duty_records[0].team_name if on_duty_records else ""
        on_duty_record = on_duty_records[0] if on_duty_records else None

        # 全局在值人员 ID 集合
        on_duty_ids = set()
        if on_duty_record:
            if on_duty_record.team_leader_id:
                on_duty_ids.add(on_duty_record.team_leader_id)
            for uid in on_duty_record.person_id_list:
                on_duty_ids.add(uid)
            for uid in on_duty_record.temp_person_id_list:
                on_duty_ids.add(uid)

        # 遍历所有排班记录，构建 teams_data
        teams_data = []
        seen_teams = set()
        for rec in records:
            if rec.team_name in seen_teams:
                continue
            seen_teams.add(rec.team_name)

            on_duty_personnel = []
            if rec.schedule_status == "Y":
                # 在值：核心成员 + 临时借调
                if rec.team_leader_id and rec.team_leader_name:
                    on_duty_personnel.append({
                        "id": rec.team_leader_id, "name": rec.team_leader_name,
                        "role": "值班长", "team": rec.team_name,
                        "type": "core", "status": "on-duty"
                    })
                for i, uid in enumerate(rec.person_id_list):
                    name = rec.person_name_list[i] if i < len(rec.person_name_list) else f"人员{uid}"
                    on_duty_personnel.append({
                        "id": uid, "name": name,
                        "role": "值班人员", "team": rec.team_name,
                        "type": "core", "status": "on-duty"
                    })
                for uid, name in zip(rec.temp_person_id_list, rec.temp_person_name_list):
                    home_team = rec.team_name
                    for t in all_teams:
                        if uid == t.team_leader_id or uid in t.person_id_list:
                            home_team = t.team_name
                            break
                    on_duty_personnel.append({
                        "id": uid, "name": name,
                        "role": "临时值班人员", "team": home_team,
                        "type": "temp", "status": "on-duty"
                    })

            teams_data.append({
                "record_id": rec.record_id,
                "team_name": rec.team_name,
                "shift_type": detect_shift_type(rec.on_duty_time),
                "schedule_status": rec.schedule_status,
                "on_duty_time": rec.on_duty_time.strftime("%H:%M") if rec.on_duty_time else "",
                "off_duty_time": rec.off_duty_time.strftime("%H:%M") if rec.off_duty_time else "",
                "on_duty_count": len(on_duty_personnel),
                "on_duty_personnel": on_duty_personnel
            })

        # 休息人员：所有班组中不在在值排班中的人
        resting_personnel = []
        for t in all_teams:
            if t.team_leader_id and t.team_leader_id not in on_duty_ids:
                resting_personnel.append({
                    "id": t.team_leader_id, "name": t.team_leader_name,
                    "role": "值班长", "team": t.team_name, "status": "rest"
                })
                on_duty_ids.add(t.team_leader_id)
            for uid, name in zip(t.person_id_list, t.person_name_list):
                if uid not in on_duty_ids:
                    resting_personnel.append({
                        "id": uid, "name": name,
                        "role": "值班人员", "team": t.team_name, "status": "rest"
                    })
                    on_duty_ids.add(uid)

        return json.dumps({
            "code": 0,
            "date": target_date.strftime("%Y-%m-%d"),
            "on_duty_team_name": on_duty_team_name,
            "teams": teams_data,
            "resting_personnel": resting_personnel,
            "resting_count": len(resting_personnel)
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"code": 1, "error": str(e)}, ensure_ascii=False)
@tool
def add_temp_personnel(
    record_id: str = "",
    person_id: str = "",
    person_name: str = "",
    home_team_name: str = ""
) -> str:
    """
    跨班组临时借调 — 将其他班组休息人员加入当前当值班组作为临时值班人员
    - record_id: 目标排班记录ID
    - person_id: 人员ID
    - person_name: 人员姓名
    - home_team_name: 人员所属原始班组（仅用于记录，不改变）
    """
    try:
        if not record_id or not person_id:
            return json.dumps({"code": 1, "error": "缺少 record_id 或 person_id"}, ensure_ascii=False)

        record = ScheduleDataProvider.get_record_by_id(record_id)
        if not record:
            return json.dumps({"code": 1, "error": f"未找到排班记录: {record_id}"}, ensure_ascii=False)

        if record.schedule_status != "Y":
            return json.dumps({"code": 1, "error": f"{record.team_name} 已交班，无法添加人员"}, ensure_ascii=False)

        # 检查此人是否已是核心成员
        if person_id in record.person_id_list or person_id == record.team_leader_id:
            return json.dumps({
                "code": 0,
                "msg": f"{person_name} 已是 {record.team_name} 核心成员，无需临时借调"
            }, ensure_ascii=False)

        # 检查是否已临时加入
        if person_id in record.temp_person_id_list:
            return json.dumps({
                "code": 0,
                "msg": f"{person_name} 已是 {record.team_name} 临时值班人员"
            }, ensure_ascii=False)

        record.add_temp_person(person_id, person_name)
        ScheduleDataProvider.update_record(record)

        return json.dumps({
            "code": 0,
            "msg": f"已将 {person_name}（{home_team_name}）临时加入 {record.team_name} 作为值班人员",
            "record_id": record_id,
            "team_name": record.team_name,
            "temp_person_ids": record.temp_person_ids,
            "temp_person_names": record.temp_person_names
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"code": 1, "error": str(e)}, ensure_ascii=False)


@tool
def remove_temp_personnel(
    record_id: str = "",
    person_id: str = ""
) -> str:
    """
    移除临时值班人员 — 将临时借调人员从当值班组中移除（设为休息）
    - record_id: 排班记录ID
    - person_id: 人员ID
    """
    try:
        if not record_id or not person_id:
            return json.dumps({"code": 1, "error": "缺少 record_id 或 person_id"}, ensure_ascii=False)

        record = ScheduleDataProvider.get_record_by_id(record_id)
        if not record:
            return json.dumps({"code": 1, "error": f"未找到排班记录: {record_id}"}, ensure_ascii=False)

        if record.schedule_status != "Y":
            return json.dumps({"code": 1, "error": f"{record.team_name} 已交班"}, ensure_ascii=False)

        # 查找人员姓名
        person_name = person_id
        temp_names = record.temp_person_name_list
        temp_ids = record.temp_person_id_list
        if person_id in temp_ids:
            idx = temp_ids.index(person_id)
            person_name = temp_names[idx] if idx < len(temp_names) else person_id

        removed = record.remove_temp_person(person_id)
        if not removed:
            return json.dumps({
                "code": 0,
                "msg": f"{person_name} 不是 {record.team_name} 的临时值班人员"
            }, ensure_ascii=False)

        ScheduleDataProvider.update_record(record)

        return json.dumps({
            "code": 0,
            "msg": f"已将 {person_name} 从 {record.team_name} 临时值班人员中移除，设为休息",
            "record_id": record_id,
            "team_name": record.team_name
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"code": 1, "error": str(e)}, ensure_ascii=False)


@tool
def end_shift(record_id: str = "") -> str:
    """
    交班操作 — 结束当前班次，自动清除所有临时借调人员
    - record_id: 排班记录ID
    """
    try:
        if not record_id:
            return json.dumps({"code": 1, "error": "缺少 record_id"}, ensure_ascii=False)

        record = ScheduleDataProvider.get_record_by_id(record_id)
        if not record:
            return json.dumps({"code": 1, "error": f"未找到排班记录: {record_id}"}, ensure_ascii=False)

        if record.schedule_status != "Y":
            return json.dumps({"code": 0, "msg": f"{record.team_name} 已是交班状态"}, ensure_ascii=False)

        shift_result = record.end_shift()
        ScheduleDataProvider.update_record(record)

        return json.dumps({
            "code": 0,
            "msg": shift_result["msg"],
            "team_name": shift_result["team_name"],
            "cleared_temp": shift_result["cleared_temp"],
            "change_time": shift_result["change_time"]
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"code": 1, "error": str(e)}, ensure_ascii=False)