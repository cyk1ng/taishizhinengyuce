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
    def all_personnel(self) -> list[dict]:
        """完整排班人员列表"""
        people = []
        if self.team_leader_id and self.team_leader_name:
            people.append({"id": self.team_leader_id, "name": self.team_leader_name, "role": "值班长"})
        ids = self.person_id_list
        names = self.person_name_list
        for i, uid in enumerate(ids):
            name = names[i] if i < len(names) else f"人员{uid}"
            people.append({"id": uid, "name": name, "role": "值班人员"})
        return people


# ═══════════════════════════════════════════════
#  班次类型自动识别
# ═══════════════════════════════════════════════

def detect_shift_type(on_duty_time: Optional[datetime]) -> str:
    """
    根据 ON_DUTY_TIME 自动识别班次类型

    规则：
      - 06:00-09:59  → 早班
      - 10:00-14:59  → 中班
      - 15:00-23:59  → 晚班
      - 00:00-05:59  → 夜班
    """
    if on_duty_time is None:
        return "未知"
    hour = on_duty_time.hour
    if 6 <= hour < 10:
        return "早班"
    elif 10 <= hour < 15:
        return "中班"
    elif 15 <= hour < 24:
        return "晚班"
    else:  # 00:00-05:59
        return "夜班"


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


# ═══════════════════════════════════════════════
#  数据提供层 — 模拟 Oracle 查询
# ═══════════════════════════════════════════════

class ScheduleDataProvider:
    """排班数据提供层（模拟 Oracle 的 OC_SCHEDULE_TEAM / OC_SCHEDULE_RECORD）"""

    @staticmethod
    def get_teams(city_dept_id: str = "") -> list[OcScheduleTeam]:
        """
        获取班组信息 — 对应 SELECT * FROM OC_SCHEDULE_TEAM WHERE ENABLE_FLAG='Y'
        """
        # 模拟数据：6个班组 A-F
        teams = [
            OcScheduleTeam(
                team_id="T001", team_name="A班",
                team_leader_id="U001", team_leader_name="张队",
                create_busi_dept_id="D001", create_busi_dept_name="广州供电局",
                enable_flag="Y",
                other_person_ids="U101,U102,U103",
                other_person_names="张三,李四,王五"
            ),
            OcScheduleTeam(
                team_id="T002", team_name="B班",
                team_leader_id="U002", team_leader_name="李队",
                create_busi_dept_id="D001", create_busi_dept_name="广州供电局",
                enable_flag="Y",
                other_person_ids="U201,U202,U203",
                other_person_names="赵六,钱七,孙八"
            ),
            OcScheduleTeam(
                team_id="T003", team_name="C班",
                team_leader_id="U003", team_leader_name="王队",
                create_busi_dept_id="D001", create_busi_dept_name="广州供电局",
                enable_flag="Y",
                other_person_ids="U301,U302,U303",
                other_person_names="周九,吴十,郑十一"
            ),
            OcScheduleTeam(
                team_id="T004", team_name="D班",
                team_leader_id="U004", team_leader_name="刘队",
                create_busi_dept_id="D001", create_busi_dept_name="广州供电局",
                enable_flag="Y",
                other_person_ids="U401,U402,U403",
                other_person_names="冯十二,陈十三,褚十四"
            ),
            OcScheduleTeam(
                team_id="T005", team_name="E班",
                team_leader_id="U005", team_leader_name="陈队",
                create_busi_dept_id="D001", create_busi_dept_name="广州供电局",
                enable_flag="Y",
                other_person_ids="U501,U502,U503",
                other_person_names="卫十五,蒋十六,沈十七"
            ),
            OcScheduleTeam(
                team_id="T006", team_name="F班",
                team_leader_id="U006", team_leader_name="杨队",
                create_busi_dept_id="D001", create_busi_dept_name="广州供电局",
                enable_flag="Y",
                other_person_ids="U601,U602,U603",
                other_person_names="韩十八,杨十九,朱二十"
            ),
        ]
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
        获取排班记录 — 对应 SELECT * FROM OC_SCHEDULE_RECORD
        WHERE ON_DUTY_TIME BETWEEN :start AND :end
        """
        records: list[OcScheduleRecord] = []
        teams = ScheduleDataProvider.get_teams(city_dept_id)
        current = start_date
        idx = 0
        while current <= end_date:
            for i, team in enumerate(teams):
                if current > end_date:
                    break
                # 模拟早/中/晚三个班次
                for hour_offset, shift_label in [(8, "早班"), (12, "中班"), (18, "晚班")]:
                    on_duty = datetime(current.year, current.month, current.day, hour_offset, 0, 0)
                    off_duty = on_duty + timedelta(hours=8)
                    idx += 1
                    records.append(OcScheduleRecord(
                        record_id=f"SR{current.strftime('%Y%m%d')}_{team.team_id}_{hour_offset}",
                        dis_org_id=team.create_busi_dept_id,
                        dis_org_name=team.create_busi_dept_name,
                        team_id=team.team_id,
                        team_name=team.team_name,
                        schedule_status="Y",
                        on_duty_time=on_duty,
                        off_duty_time=off_duty,
                        team_leader_id=team.team_leader_id,
                        team_leader_name=team.team_leader_name,
                        other_person_ids=team.other_person_ids,
                        other_person_names=team.other_person_names,
                    ))
            current += timedelta(days=1)
        return records

    @staticmethod
    def get_current_on_duty(city_dept_id: str = "") -> list[OcScheduleRecord]:
        """获取当前正在值勤的排班记录（SCHEDULE_STATUS='Y'）"""
        today = date.today()
        records = ScheduleDataProvider.get_records(today, today, city_dept_id)
        return [r for r in records if r.schedule_status == "Y"]

    @staticmethod
    def save_records(records: list[OcScheduleRecord]) -> int:
        """
        保存排班记录 — 对应 INSERT INTO OC_SCHEDULE_RECORD
        返回写入条数
        """
        return len(records)


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

                new_records.append(OcScheduleRecord(
                    record_id=record_id,
                    dis_org_id=team.create_busi_dept_id,
                    dis_org_name=team.create_busi_dept_name,
                    team_id=team.team_id,
                    team_name=team.team_name,
                    schedule_status="Y",
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
            ))

        saved = ScheduleDataProvider.save_records(records)
        return json.dumps({"code": 0, "saved": saved, "msg": f"成功保存 {saved} 条排班记录"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"code": 1, "error": str(e)}, ensure_ascii=False)