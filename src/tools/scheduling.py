"""
智能排班管理模块 - 配网调度业务量智能预测系统

排班规则：
1. 班组数量不固定，可随意设置
2. 一个班组一天只能排一次班（早/中/晚三选一）
3. 每班人员要求：
   - 值班长(3)：必须1人，只能1人
   - 正值(2)：至少1人，可多人
   - 副值(1)：至少1人，可多人
   - 其他(0)：可选，按需配置
4. 约束条件：
   - 最大连续工作天数：6天
   - 每周最多晚班：3次
   - 公平轮换
   - 只安排生效状态为"是"的班组

数据库表结构：
- working_user: 上班人员表
- working_groups: 班组表（含生效状态字段）
- work_schedule_recode: 排班记录表
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from langchain.tools import tool, ToolRuntime
from langchain_core.messages import HumanMessage, SystemMessage
from coze_coding_dev_sdk import LLMClient
from coze_coding_utils.runtime_ctx.context import new_context

# 配置文件路径
SCHEDULE_CONFIG = "assets/schedule_config.json"


# ============================================================
# 数据模型
# ============================================================

class WorkingUser:
    """
    上班人员表 (working_user)
    
    字段：
    - MK_ID: 主键 (varchar(36))
    - USER_ID: 用户ID (varchar(36))
    - USER_NAME: 用户名 (varchar(255))
    - GROUP: 所属班次 (varchar(255))
    - ID_LEADER: 值班类型 (int)
        - 0: 其他值班人员
        - 1: 副值
        - 2: 正值
        - 3: 值班长
    - CITY_DEPT_ID: 所属地市ID (varchar(36))
    - CITY_DEPT_NAME: 所属地市名字 (varchar(255))
    """
    
    ROLE_NAMES = {
        0: "其他值班人员",
        1: "副值",
        2: "正值",
        3: "值班长"
    }
    
    def __init__(self, data: Dict):
        self.mk_id = data.get("MK_ID", "")
        self.user_id = data.get("USER_ID", "")
        self.user_name = data.get("USER_NAME", "")
        self.group = data.get("GROUP", "")
        self.id_leader = data.get("ID_LEADER", 0)
        self.city_dept_id = data.get("CITY_DEPT_ID", "")
        self.city_dept_name = data.get("CITY_DEPT_NAME", "")
    
    @property
    def role_name(self) -> str:
        return self.ROLE_NAMES.get(self.id_leader, "未知")
    
    def to_dict(self) -> Dict:
        return {
            "mk_id": self.mk_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "group": self.group,
            "id_leader": self.id_leader,
            "role_name": self.role_name,
            "city_dept_id": self.city_dept_id,
            "city_dept_name": self.city_dept_name
        }


class WorkingGroup:
    """
    班组表 (working_groups)
    
    关键规则：
    - 班组数量不固定
    - 一个班组一天只能排一次班
    - 只有生效状态为"是"的班组才会被安排
    """
    
    def __init__(self, data: Dict):
        self.group_id = data.get("GROUP_ID", "")
        self.group_name = data.get("GROUP_NAME", data.get("GROUP", ""))
        self.is_active = self._parse_active_status(data.get("IS_ACTIVE", "是"))
        self.city_dept_id = data.get("CITY_DEPT_ID", "")
        self.city_dept_name = data.get("CITY_DEPT_NAME", "")
        self.members: List[WorkingUser] = []
    
    def _parse_active_status(self, status) -> bool:
        """解析生效状态"""
        if isinstance(status, bool):
            return status
        if isinstance(status, int):
            return status == 1
        if isinstance(status, str):
            return status in ["是", "YES", "Yes", "yes", "1", "TRUE", "True", "true"]
        return True
    
    def get_members_by_role(self, role_id: int) -> List[WorkingUser]:
        """获取指定角色的成员"""
        return [m for m in self.members if m.id_leader == role_id]
    
    def to_dict(self) -> Dict:
        return {
            "group_id": self.group_id,
            "group_name": self.group_name,
            "is_active": self.is_active,
            "member_count": len(self.members),
            "members": [m.to_dict() for m in self.members],
            "city_dept_id": self.city_dept_id,
            "city_dept_name": self.city_dept_name
        }


class ScheduleRecord:
    """排班记录表 (work_schedule_recode)"""
    
    def __init__(self, data: Dict):
        self.record_id = data.get("RECORD_ID", "")
        self.user_id = data.get("USER_ID", "")
        self.user_name = data.get("USER_NAME", "")
        self.group_name = data.get("GROUP_NAME", data.get("GROUP", ""))
        self.schedule_date = data.get("SCHEDULE_DATE", "")
        self.shift_type = data.get("SHIFT_TYPE", "")  # 早班/中班/晚班
        self.status = data.get("STATUS", "计划")
        self.id_leader = data.get("ID_LEADER", 0)
        self.city_dept_id = data.get("CITY_DEPT_ID", "")
        self.city_dept_name = data.get("CITY_DEPT_NAME", "")
    
    def to_dict(self) -> Dict:
        return {
            "record_id": self.record_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "group_name": self.group_name,
            "schedule_date": self.schedule_date,
            "shift_type": self.shift_type,
            "status": self.status,
            "id_leader": self.id_leader,
            "role_name": WorkingUser.ROLE_NAMES.get(self.id_leader, "未知"),
            "city_dept_id": self.city_dept_id,
            "city_dept_name": self.city_dept_name
        }


# ============================================================
# 配置管理
# ============================================================

class ScheduleConfig:
    """排班配置管理"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(
            os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"),
            SCHEDULE_CONFIG
        )
        self._config = self._load_config()
    
    def _load_config(self) -> Dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        return {
            "shift_structure": {
                "shifts_per_day": 3,
                "shift_names": ["早班", "中班", "晚班"],
                "shift_times": {
                    "早班": {"start": "08:00", "end": "16:00"},
                    "中班": {"start": "16:00", "end": "24:00"},
                    "晚班": {"start": "00:00", "end": "08:00"}
                }
            },
            "staffing_requirements": {
                "leader_required": 1,      # 值班长必须1人
                "leader_max": 1,           # 值班长最多1人
                "zhizhi_min": 1,           # 正值至少1人
                "fuzhi_min": 1,            # 副值至少1人
                "other_optional": True     # 其他人员可选
            },
            "constraints": {
                "max_consecutive_days": 6,
                "max_night_shifts_per_week": 3,
                "fair_rotation": True
            }
        }
    
    @property
    def constraints(self) -> Dict:
        return self._config.get("constraints", {})


# ============================================================
# 数据库查询
# ============================================================

class ScheduleDataProvider:
    """排班数据提供者"""
    
    @staticmethod
    def _get_db_session():
        """获取数据库会话"""
        from storage.database.db import get_session, is_database_connected
        if not is_database_connected():
            return None
        return get_session()
    
    @staticmethod
    def get_working_users(city_dept_id: Optional[str] = None) -> List[WorkingUser]:
        """从数据库获取所有上班人员"""
        session = ScheduleDataProvider._get_db_session()
        
        if session:
            try:
                from sqlalchemy import text
                
                if city_dept_id:
                    sql = text("""
                        SELECT MK_ID, USER_ID, USER_NAME, `GROUP`, ID_LEADER, 
                               CITY_DEPT_ID, CITY_DEPT_NAME
                        FROM working_user 
                        WHERE CITY_DEPT_ID = :dept_id
                    """)
                    result = session.execute(sql, {"dept_id": city_dept_id})
                else:
                    sql = text("""
                        SELECT MK_ID, USER_ID, USER_NAME, `GROUP`, ID_LEADER, 
                               CITY_DEPT_ID, CITY_DEPT_NAME
                        FROM working_user
                    """)
                    result = session.execute(sql)
                
                users = [WorkingUser(dict(row._mapping)) for row in result]
                return users
                
            except Exception as e:
                import logging
                logging.error(f"查询 working_user 表失败: {e}")
            finally:
                session.close()
        
        return []
    
    @staticmethod
    def get_working_groups(city_dept_id: Optional[str] = None) -> List[WorkingGroup]:
        """
        从数据库获取班组信息
        
        关键：只返回生效状态为"是"的班组
        """
        session = ScheduleDataProvider._get_db_session()
        
        if session:
            try:
                from sqlalchemy import text
                
                # 查询班组表，获取生效的班组
                if city_dept_id:
                    sql = text("""
                        SELECT GROUP_ID, GROUP_NAME, IS_ACTIVE, 
                               CITY_DEPT_ID, CITY_DEPT_NAME
                        FROM working_groups
                        WHERE IS_ACTIVE IN ('是', 'YES', 'Yes', 'yes', '1', 1, TRUE)
                              AND (CITY_DEPT_ID = :dept_id OR :dept_id = '')
                    """)
                    result = session.execute(sql, {"dept_id": city_dept_id})
                else:
                    sql = text("""
                        SELECT GROUP_ID, GROUP_NAME, IS_ACTIVE, 
                               CITY_DEPT_ID, CITY_DEPT_NAME
                        FROM working_groups
                        WHERE IS_ACTIVE IN ('是', 'YES', 'Yes', 'yes', '1', 1, TRUE)
                    """)
                    result = session.execute(sql)
                
                groups = []
                for row in result:
                    group_data = dict(row._mapping)
                    group = WorkingGroup(group_data)
                    groups.append(group)
                
                # 获取所有用户并分配到对应班组
                all_users = ScheduleDataProvider.get_working_users(city_dept_id)
                for group in groups:
                    group.members = [u for u in all_users if u.group == group.group_name]
                
                return groups
                
            except Exception as e:
                import logging
                logging.error(f"查询 working_groups 表失败: {e}")
            finally:
                session.close()
        
        return []
    
    @staticmethod
    def get_schedule_records(
        start_date: str,
        end_date: str,
        city_dept_id: Optional[str] = None
    ) -> List[ScheduleRecord]:
        """从数据库获取排班记录"""
        session = ScheduleDataProvider._get_db_session()
        
        if session:
            try:
                from sqlalchemy import text
                
                if city_dept_id:
                    sql = text("""
                        SELECT RECORD_ID, USER_ID, USER_NAME, GROUP_NAME,
                               SCHEDULE_DATE, SHIFT_TYPE, STATUS, ID_LEADER,
                               CITY_DEPT_ID, CITY_DEPT_NAME
                        FROM work_schedule_recode
                        WHERE SCHEDULE_DATE BETWEEN :start AND :end
                              AND (CITY_DEPT_ID = :dept_id OR :dept_id = '')
                        ORDER BY SCHEDULE_DATE, SHIFT_TYPE
                    """)
                    result = session.execute(sql, {
                        "start": start_date,
                        "end": end_date,
                        "dept_id": city_dept_id
                    })
                else:
                    sql = text("""
                        SELECT RECORD_ID, USER_ID, USER_NAME, GROUP_NAME,
                               SCHEDULE_DATE, SHIFT_TYPE, STATUS, ID_LEADER,
                               CITY_DEPT_ID, CITY_DEPT_NAME
                        FROM work_schedule_recode
                        WHERE SCHEDULE_DATE BETWEEN :start AND :end
                        ORDER BY SCHEDULE_DATE, SHIFT_TYPE
                    """)
                    result = session.execute(sql, {
                        "start": start_date,
                        "end": end_date
                    })
                
                records = [ScheduleRecord(dict(row._mapping)) for row in result]
                return records
                
            except Exception as e:
                import logging
                logging.error(f"查询 work_schedule_recode 表失败: {e}")
            finally:
                session.close()
        
        return []


# ============================================================
# 智能排班引擎
# ============================================================

class IntelligentScheduleEngine:
    """
    智能排班引擎
    
    核心规则：
    1. 一个班组一天只能排一次班
    2. 每班：1名值班长(必须且只能1人) + N名正值 + N名副值 + 可选其他人员
    3. 最大连续工作6天
    4. 每周最多3次晚班
    5. 公平轮换
    6. 只安排生效的班组
    """
    
    def __init__(self, config: Optional[ScheduleConfig] = None):
        self.config = config or ScheduleConfig()
        self.llm_client = None
    
    def _init_llm_client(self, ctx):
        if self.llm_client is None:
            self.llm_client = LLMClient(ctx=ctx)
        return self.llm_client
    
    def _check_group_can_work(
        self,
        group: WorkingGroup,
        date: datetime,
        recent_records: Dict[str, List[ScheduleRecord]]
    ) -> Tuple[bool, str]:
        """
        检查班组是否可以排班
        
        返回: (是否可以排班, 原因)
        """
        group_name = group.group_name
        group_records = recent_records.get(group_name, [])
        
        # 1. 检查是否今天已经排班（一个班组一天只能排一次）
        today_str = date.strftime("%Y-%m-%d")
        today_records = [r for r in group_records if r.schedule_date == today_str]
        if today_records:
            return False, f"班组{group_name}今天已排{today_records[0].shift_type}"
        
        # 2. 检查连续工作天数（最大6天）
        consecutive_days = self._count_consecutive_work_days(group_records, date)
        if consecutive_days >= 6:
            return False, f"班组{group_name}已连续工作{consecutive_days}天，需休息"
        
        # 3. 检查本周晚班次数（最多3次）
        week_night_shifts = self._count_week_night_shifts(group_records, date)
        if week_night_shifts >= 3:
            return False, f"班组{group_name}本周晚班已达{week_night_shifts}次"
        
        return True, "可以排班"
    
    def _count_consecutive_work_days(
        self,
        records: List[ScheduleRecord],
        date: datetime
    ) -> int:
        """计算连续工作天数"""
        if not records:
            return 0
        
        # 按日期排序
        sorted_dates = sorted(set(r.schedule_date for r in records), reverse=True)
        
        count = 0
        check_date = date - timedelta(days=1)
        
        for d in sorted_dates:
            d_date = datetime.strptime(d, "%Y-%m-%d")
            if d_date == check_date:
                count += 1
                check_date -= timedelta(days=1)
            elif d_date < check_date:
                break
        
        return count
    
    def _count_week_night_shifts(
        self,
        records: List[ScheduleRecord],
        date: datetime
    ) -> int:
        """计算本周晚班次数"""
        # 获取本周开始日期（周一）
        week_start = date - timedelta(days=date.weekday())
        week_end = week_start + timedelta(days=6)
        
        count = 0
        for record in records:
            record_date = datetime.strptime(record.schedule_date, "%Y-%m-%d")
            if week_start <= record_date <= week_end and record.shift_type == "晚班":
                count += 1
        
        return count
    
    def _select_staff_for_shift(
        self,
        group: WorkingGroup,
        shift_type: str
    ) -> Dict:
        """
        为班次选择人员
        
        规则：
        - 值班长：必须1人，只能1人
        - 正值：至少1人，可多人
        - 副值：至少1人，可多人
        - 其他：可选
        """
        leaders = group.get_members_by_role(3)  # 值班长
        zhizhi = group.get_members_by_role(2)   # 正值
        fuzhi = group.get_members_by_role(1)    # 副值
        others = group.get_members_by_role(0)   # 其他
        
        selected = {
            "shift_type": shift_type,
            "group_name": group.group_name,
            "leader": None,
            "zhizhi": [],
            "fuzhi": [],
            "others": [],
            "total_count": 0
        }
        
        # 1. 选择值班长（必须1人，只能1人）
        if leaders:
            selected["leader"] = leaders[0].to_dict()
        
        # 2. 选择正值（至少1人）
        if zhizhi:
            selected["zhizhi"] = [z.to_dict() for z in zhizhi[:2]]  # 最多2人
        
        # 3. 选择副值（至少1人）
        if fuzhi:
            selected["fuzhi"] = [f.to_dict() for f in fuzhi[:2]]  # 最多2人
        
        # 4. 选择其他人员（可选）
        if others:
            selected["others"] = [o.to_dict() for o in others[:1]]  # 最多1人
        
        selected["total_count"] = (
            (1 if selected["leader"] else 0) +
            len(selected["zhizhi"]) +
            len(selected["fuzhi"]) +
            len(selected["others"])
        )
        
        return selected
    
    def _build_schedule_prompt(
        self,
        prediction_summary: Dict,
        daily_predictions: List[Dict],
        active_groups: List[Dict],
        constraints: Dict
    ) -> str:
        """构建排班提示词"""
        
        return f"""
你是配网调度排班专家，请严格按照以下规则生成排班方案。

## 排班规则（必须严格遵守）

### 1. 班组规则
- 一个班组一天**只能排一次班**（早班/中班/晚班三选一）
- 只安排**生效状态为"是"**的班组
- 班组公平轮换，避免某班组连续工作过多

### 2. 每班人员配置（硬性要求）
- **值班长(ID_LEADER=3)**：必须1人，只能1人
- **正值(ID_LEADER=2)**：至少1人，可以多人
- **副值(ID_LEADER=1)**：至少1人，可以多人
- **其他(ID_LEADER=0)**：可选，按需配置

### 3. 约束条件
- 最大连续工作天数：{constraints.get('max_consecutive_days', 6)}天
- 每周最多晚班次数：{constraints.get('max_night_shifts_per_week', 3)}次
- 公平轮换

## 业务量预测摘要
{json.dumps(prediction_summary, ensure_ascii=False, indent=2)}

## 每日预测详情
{json.dumps(daily_predictions, ensure_ascii=False, indent=2)}

## 生效班组列表（is_active=true）
{json.dumps(active_groups, ensure_ascii=False, indent=2)}

## 输出格式（JSON）
```json
{{
  "schedule_summary": {{
    "total_groups_used": 数字,
    "peak_day": "YYYY-MM-DD",
    "peak_staff_count": 数字,
    "schedule_period": "开始 至 结束"
  }},
  "daily_schedules": [
    {{
      "date": "YYYY-MM-DD",
      "predicted_dispatches": 数字,
      "risk_level": "低/中/高",
      "shifts": {{
        "早班": {{
          "group_name": "班组名",
          "leader": {{"user_id": "ID", "user_name": "姓名"}},
          "zhizhi": [{{"user_id": "ID", "user_name": "姓名"}}],
          "fuzhi": [{{"user_id": "ID", "user_name": "姓名"}}],
          "others": [],
          "total_count": 数字
        }},
        "中班": {{...}},
        "晚班": {{...}}
      }},
      "notes": "说明"
    }}
  ],
  "rotation_check": {{
    "max_consecutive_days": 数字,
    "max_week_night_shifts": 数字,
    "fairness_score": 0.0-1.0
  }},
  "recommendations": ["建议1", "建议2"]
}}
```

请生成排班方案：
"""
    
    def generate_schedule(
        self,
        prediction_result: Dict,
        city_dept_id: Optional[str] = None,
        ctx=None
    ) -> Dict:
        """生成智能排班方案"""
        try:
            # 获取生效的班组
            groups = ScheduleDataProvider.get_working_groups(city_dept_id)
            
            if not groups:
                return {
                    "error": "没有生效的班组",
                    "message": "请确保 working_groups 表中有 IS_ACTIVE='是' 的班组"
                }
            
            # 检查每个班组的人员配置是否满足要求
            valid_groups = []
            for group in groups:
                leaders = group.get_members_by_role(3)
                zhizhi = group.get_members_by_role(2)
                fuzhi = group.get_members_by_role(1)
                
                if leaders and zhizhi and fuzhi:
                    valid_groups.append(group)
                else:
                    group_info = {
                        "group_name": group.group_name,
                        "has_leader": len(leaders) > 0,
                        "has_zhizhi": len(zhizhi) > 0,
                        "has_fuzhi": len(fuzhi) > 0,
                        "warning": "人员配置不满足要求（需要至少1名值班长、1名正值、1名副值）"
                    }
                    valid_groups.append(group)  # 仍然加入，但标记警告
            
            # 提取预测数据
            prediction_summary = prediction_result.get("prediction_summary", {})
            daily_predictions = prediction_result.get("daily_predictions", [])
            
            # 初始化LLM
            client = self._init_llm_client(ctx)
            
            # 构建提示词
            prompt = self._build_schedule_prompt(
                prediction_summary,
                daily_predictions,
                [g.to_dict() for g in valid_groups],
                self.config.constraints
            )
            
            # 调用LLM
            messages = [
                SystemMessage(content="你是专业的配网调度排班专家，严格遵循排班规则。"),
                HumanMessage(content=prompt)
            ]
            
            response = client.invoke(
                messages=messages,
                model="doubao-seed-1-8-251228",
                temperature=0.3,
                max_completion_tokens=6000
            )
            
            # 解析响应
            content = response.content
            if isinstance(content, list):
                content = " ".join(
                    item.get("text", "") 
                    for item in content 
                    if isinstance(item, dict) and item.get("type") == "text"
                )
            
            # 提取JSON
            json_start = content.find("```json")
            json_end = content.find("```", json_start + 7)
            
            if json_start != -1 and json_end != -1:
                json_str = content[json_start + 7:json_end].strip()
                schedule_result = json.loads(json_str)
            else:
                schedule_result = json.loads(content)
            
            # 添加元数据
            schedule_result["metadata"] = {
                "generation_time": datetime.now().isoformat(),
                "total_active_groups": len(groups),
                "valid_groups": len(valid_groups),
                "city_dept_id": city_dept_id
            }
            
            return schedule_result
            
        except Exception as e:
            return {
                "error": str(e),
                "message": "排班生成失败",
                "timestamp": datetime.now().isoformat()
            }


# ============================================================
# 工具函数
# ============================================================

@tool
def get_schedule_staff_info(
    city_dept_id: str = "",
    runtime: ToolRuntime = None
) -> str:
    """
    获取排班人员信息（包括生效班组）
    
    参数：
    - city_dept_id: 所属地市ID（可选）
    
    返回：人员信息JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="get_schedule_staff_info")
    
    try:
        from storage.database.db import is_database_connected
        
        db_connected = is_database_connected()
        users = ScheduleDataProvider.get_working_users(city_dept_id if city_dept_id else None)
        groups = ScheduleDataProvider.get_working_groups(city_dept_id if city_dept_id else None)
        
        # 统计角色分布
        role_stats = {}
        for user in users:
            role_name = user.role_name
            role_stats[role_name] = role_stats.get(role_name, 0) + 1
        
        # 检查每个班组的人员配置
        group_check = []
        for group in groups:
            leaders = group.get_members_by_role(3)
            zhizhi = group.get_members_by_role(2)
            fuzhi = group.get_members_by_role(1)
            
            group_check.append({
                "group_name": group.group_name,
                "is_active": group.is_active,
                "member_count": len(group.members),
                "leader_count": len(leaders),
                "zhizhi_count": len(zhizhi),
                "fuzhi_count": len(fuzhi),
                "is_valid": len(leaders) >= 1 and len(zhizhi) >= 1 and len(fuzhi) >= 1,
                "warning": None if (len(leaders) >= 1 and len(zhizhi) >= 1 and len(fuzhi) >= 1) 
                          else "人员不足：需要至少1名值班长、1名正值、1名副值"
            })
        
        if len(users) == 0:
            result = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "city_dept_id": city_dept_id or "全部",
                "database_connected": db_connected,
                "staff_summary": {
                    "total_users": 0,
                    "active_groups": 0,
                    "role_distribution": {}
                },
                "users": [],
                "groups": [],
                "group_validation": [],
                "message": "未查询到人员数据",
                "setup_guide": {
                    "step1": "检查 .env 中的数据库配置",
                    "step2": "确保 working_user 表存在且有数据",
                    "step3": "确保 working_groups 表有 IS_ACTIVE='是' 的记录"
                }
            }
        else:
            result = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "city_dept_id": city_dept_id or "全部",
                "database_connected": db_connected,
                "staff_summary": {
                    "total_users": len(users),
                    "active_groups": len(groups),
                    "role_distribution": role_stats
                },
                "users": [u.to_dict() for u in users],
                "groups": [g.to_dict() for g in groups],
                "group_validation": group_check
            }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "获取人员信息失败"
        }, ensure_ascii=False)


@tool
def get_existing_schedule(
    start_date: str,
    end_date: str,
    city_dept_id: str = "",
    runtime: ToolRuntime = None
) -> str:
    """
    获取现有排班记录
    
    参数：
    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    - city_dept_id: 所属地市ID（可选）
    
    返回：排班记录JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="get_existing_schedule")
    
    try:
        records = ScheduleDataProvider.get_schedule_records(
            start_date,
            end_date,
            city_dept_id if city_dept_id else None
        )
        
        # 按日期和班次组织
        schedule_by_date = {}
        for record in records:
            date = record.schedule_date
            shift = record.shift_type
            
            if date not in schedule_by_date:
                schedule_by_date[date] = {}
            if shift not in schedule_by_date[date]:
                schedule_by_date[date][shift] = []
            
            schedule_by_date[date][shift].append(record.to_dict())
        
        # 统计班组工作情况
        group_work_stats = {}
        for record in records:
            group_name = record.group_name
            if group_name not in group_work_stats:
                group_work_stats[group_name] = {
                    "total_shifts": 0,
                    "dates": set(),
                    "shift_types": {}
                }
            group_work_stats[group_name]["total_shifts"] += 1
            group_work_stats[group_name]["dates"].add(record.schedule_date)
            group_work_stats[group_name]["shift_types"][record.shift_type] = \
                group_work_stats[group_name]["shift_types"].get(record.shift_type, 0) + 1
        
        # 转换 set 为 list 以便 JSON 序列化
        for group_name in group_work_stats:
            group_work_stats[group_name]["dates"] = sorted(list(group_work_stats[group_name]["dates"]))
        
        result = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "date_range": {"start": start_date, "end": end_date},
            "city_dept_id": city_dept_id or "全部",
            "total_records": len(records),
            "schedule_by_date": schedule_by_date,
            "group_work_stats": group_work_stats
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "获取排班记录失败"
        }, ensure_ascii=False)


@tool
def generate_intelligent_schedule(
    prediction_result: str,
    city_dept_id: str = "",
    runtime: ToolRuntime = None
) -> str:
    """
    生成智能排班方案
    
    排班规则：
    - 一个班组一天只能排一次班（早/中/晚三选一）
    - 每班：1名值班长(必须且只能1人) + N名正值 + N名副值 + 可选其他人员
    - 最大连续工作6天，每周最多3次晚班
    - 只安排生效状态为"是"的班组
    
    参数：
    - prediction_result: 业务量预测结果JSON字符串
    - city_dept_id: 所属地市ID（可选）
    
    返回：智能排班方案JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="generate_intelligent_schedule")
    
    try:
        prediction_data = json.loads(prediction_result)
        prediction = prediction_data.get("prediction", prediction_data)
        
        engine = IntelligentScheduleEngine()
        schedule_result = engine.generate_schedule(
            prediction_result=prediction,
            city_dept_id=city_dept_id if city_dept_id else None,
            ctx=ctx
        )
        
        result = {
            "success": True,
            "generation_timestamp": datetime.now().isoformat(),
            "schedule_result": schedule_result
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "智能排班生成失败"
        }, ensure_ascii=False)


@tool
def analyze_schedule_fairness(
    schedule_records: str,
    runtime: ToolRuntime = None
) -> str:
    """
    分析排班公平性
    
    参数：
    - schedule_records: 排班记录JSON字符串
    
    返回：公平性分析报告JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="analyze_schedule_fairness")
    
    try:
        records_data = json.loads(schedule_records)
        records = records_data.get("records", [])
        
        # 统计每人工作次数
        work_count = {}
        shift_count = {}
        night_count = {}
        consecutive_days = {}
        
        for record in records:
            user_id = record.get("user_id")
            user_name = record.get("user_name")
            shift = record.get("shift_type")
            date = record.get("schedule_date")
            group = record.get("group_name", "")
            
            key = f"{user_id}_{user_name}"
            work_count[key] = work_count.get(key, 0) + 1
            
            if key not in shift_count:
                shift_count[key] = {"早班": 0, "中班": 0, "晚班": 0}
            shift_count[key][shift] = shift_count[key].get(shift, 0) + 1
            
            if shift == "晚班":
                night_count[key] = night_count.get(key, 0) + 1
            
            if group:
                if group not in consecutive_days:
                    consecutive_days[group] = set()
                consecutive_days[group].add(date)
        
        # 计算公平性指标
        counts = list(work_count.values())
        avg_work = sum(counts) / len(counts) if counts else 0
        variance = sum((c - avg_work) ** 2 for c in counts) / len(counts) if counts else 0
        balance_score = max(0, 1 - variance / (avg_work ** 2 + 1))
        
        # 检查约束违反情况
        violations = []
        for key, nights in night_count.items():
            if nights > 3:
                violations.append(f"{key} 晚班次数({nights})超过限制(3次)")
        
        result = {
            "success": True,
            "analysis_timestamp": datetime.now().isoformat(),
            "fairness_metrics": {
                "overall_balance_score": round(balance_score, 2),
                "work_count_distribution": {
                    "average": round(avg_work, 1),
                    "max": max(counts) if counts else 0,
                    "min": min(counts) if counts else 0
                },
                "night_shift_violations": violations,
                "individual_stats": {
                    user: {
                        "total_work": work_count[user],
                        "shift_breakdown": shift_count.get(user, {}),
                        "night_shifts": night_count.get(user, 0)
                    }
                    for user in work_count
                }
            },
            "fairness_assessment": {
                "level": "优秀" if balance_score >= 0.8 else "良好" if balance_score >= 0.6 else "需改进",
                "issues": violations,
                "recommendations": [] if balance_score >= 0.6 else ["建议调整排班，平衡人员工作量"]
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "公平性分析失败"
        }, ensure_ascii=False)


@tool
def export_schedule_report(
    schedule_result: str,
    output_format: str = "markdown",
    runtime: ToolRuntime = None
) -> str:
    """
    导出排班报告
    
    参数：
    - schedule_result: 排班结果JSON字符串
    - output_format: 输出格式 (markdown/json)
    
    返回：排班报告
    """
    ctx = runtime.context if runtime else new_context(method="export_schedule_report")
    
    try:
        schedule_data = json.loads(schedule_result)
        
        if output_format == "json":
            return json.dumps(schedule_data, ensure_ascii=False, indent=2)
        
        # 生成 Markdown 报告
        schedule_result_data = schedule_data.get("schedule_result", schedule_data)
        schedule_summary = schedule_result_data.get("schedule_summary", {})
        daily_schedules = schedule_result_data.get("daily_schedules", [])
        
        report = f"""# 配网调度智能排班方案

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 一、排班摘要

| 指标 | 数值 |
|------|------|
| 使用班组数 | {schedule_summary.get('total_groups_used', 'N/A')} |
| 峰值日期 | {schedule_summary.get('peak_day', 'N/A')} |
| 峰值人数 | {schedule_summary.get('peak_staff_count', 'N/A')} |
| 排班周期 | {schedule_summary.get('schedule_period', 'N/A')} |

---

## 二、每日排班详情

### 排班规则说明
- **一个班组一天只能排一次班**（早/中/晚三选一）
- **每班人员配置**：1名值班长 + N名正值 + N名副值 + 可选其他人员

---

"""
        
        for day in daily_schedules:
            date = day.get("date", "")
            dispatches = day.get("predicted_dispatches", 0)
            risk = day.get("risk_level", "中")
            shifts = day.get("shifts", {})
            notes = day.get("notes", "")
            
            report += f"""### 📅 {date}

**预测调度**: {dispatches} 次 | **风险等级**: {risk}

| 班次 | 班组 | 值班长 | 正值 | 副值 | 其他 | 总人数 |
|------|------|--------|------|------|------|--------|
"""
            
            for shift_name in ["早班", "中班", "晚班"]:
                shift_data = shifts.get(shift_name, {})
                group_name = shift_data.get("group_name", "-")
                leader = shift_data.get("leader", {})
                zhizhi = shift_data.get("zhizhi", [])
                fuzhi = shift_data.get("fuzhi", [])
                others = shift_data.get("others", [])
                total = shift_data.get("total_count", 0)
                
                leader_name = leader.get("user_name", "-") if leader else "-"
                zhizhi_names = ", ".join([z.get("user_name", "") for z in zhizhi]) or "-"
                fuzhi_names = ", ".join([f.get("user_name", "") for f in fuzhi]) or "-"
                others_names = ", ".join([o.get("user_name", "") for o in others]) or "-"
                
                report += f"| {shift_name} | {group_name} | {leader_name} | {zhizhi_names} | {fuzhi_names} | {others_names} | {total} |\n"
            
            if notes:
                report += f"\n**备注**: {notes}\n"
            report += "\n"
        
        report += """---

**报告结束**
"""
        
        return report
        
    except Exception as e:
        return f"报告导出失败: {str(e)}"
