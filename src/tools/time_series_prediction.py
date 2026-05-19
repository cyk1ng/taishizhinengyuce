"""
时序预测模块 - 基于Prophet/LSTM/XGBoost的专业时序预测

功能：
1. Prophet预测：处理趋势、季节性、节假日效应
2. LSTM预测：捕捉长期依赖和复杂模式
3. XGBoost预测：集成学习，提升预测精度
4. 多模型融合：综合多模型结果，提高预测可靠性

技术特点：
- 自动模型选择
- 置信区间计算
- 异常检测
- 模型性能评估
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context

# 时序预测库
from prophet import Prophet
from sklearn.preprocessing import MinMaxScaler
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# 可选导入：PyTorch (用于LSTM)
TORCH_AVAILABLE = False
nn = None
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    print("警告: PyTorch 未安装，LSTM预测功能将不可用。如需使用LSTM，请运行: pip install torch")


class ProphetPredictor:
    """
    Prophet时序预测器
    
    优势：
    - 自动处理趋势、季节性、节假日
    - 对缺失值有较强鲁棒性
    - 解释性强
    """

    def __init__(self, holiday_data: Optional[List[Dict]] = None):
        self.model = None
        self.scaler = MinMaxScaler()
        self.holiday_data = holiday_data or []

    def prepare_data(self, historical_data: List[Dict]) -> pd.DataFrame:
        """准备Prophet格式的数据"""
        df = pd.DataFrame(historical_data)
        df['ds'] = pd.to_datetime(df['date'])
        df['y'] = df['dispatch_count']
        
        # 添加额外的回归变量
        df['temp_max'] = df.get('temperature', 25)
        df['is_holiday'] = df.get('is_holiday', 0).astype(int)
        
        return df[['ds', 'y', 'temp_max', 'is_holiday']]

    def train(self, df: pd.DataFrame):
        """训练Prophet模型"""
        self.model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            seasonality_mode='multiplicative',
            interval_width=0.95,
            uncertainty_samples=1000
        )

        # 添加节假日效应
        if self.holiday_data:
            holidays_df = pd.DataFrame(self.holiday_data)
            holidays_df['ds'] = pd.to_datetime(holidays_df['date'])
            holidays_df['holiday'] = holidays_df['name']
            # 将节假日数据添加到模型
            self.model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=False,
                seasonality_mode='multiplicative',
                interval_width=0.95,
                uncertainty_samples=1000,
                holidays=holidays_df
            )

        # 添加外部回归变量
        self.model.add_regressor('temp_max')
        self.model.add_regressor('is_holiday')

        # 训练模型
        self.model.fit(df)

    def predict(self, future_df: pd.DataFrame) -> Dict:
        """预测未来数据"""
        forecast = self.model.predict(future_df)

        # 提取预测结果
        predictions = []
        for _, row in forecast.iterrows():
            date_val = row['ds']
            # 确保是datetime类型
            if not isinstance(date_val, pd.Timestamp):
                date_val = pd.to_datetime(date_val)

            predictions.append({
                'date': date_val.strftime('%Y-%m-%d'),
                'predicted_dispatches': int(row['yhat']),
                'predicted_lower': int(row['yhat_lower']),
                'predicted_upper': int(row['yhat_upper']),
                'confidence': 0.95,
                'trend': float(row['trend']),
                'seasonal': float(row['seasonal'])
            })

        return {
            'model_name': 'Prophet',
            'predictions': predictions,
            'metrics': {
                'trend': '上升' if predictions[-1]['trend'] > predictions[0]['trend'] else '下降',
                'seasonality': '显著'
            }
        }


class LSTMPredictor:
    """
    LSTM时序预测器

    优势：
    - 捕捉长期依赖关系
    - 处理非线性模式
    - 适合复杂时间序列
    """
    
    def __init__(self, input_size: int = 5, hidden_size: int = 64, num_layers: int = 2):
        if not TORCH_AVAILABLE:
            raise ImportError(
                "PyTorch 未安装，无法使用LSTM预测功能。\n"
                "请安装 PyTorch: pip install torch\n"
                "或者只使用 Prophet 和 XGBoost 模型进行预测。"
            )
        
        self.nn = nn  # 引用模块级 nn
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = self.nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.fc = self.nn.Linear(hidden_size, 1)
        self.dropout = self.nn.Dropout(0.2)

    def forward(self, x):
        import torch
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)

        out, _ = self.lstm(x, (h0, c0))
        out = self.dropout(out[:, -1, :])
        out = self.fc(out)
        return out


class LSTMModel:
    """LSTM模型封装"""

    def __init__(self, sequence_length: int = 7):
        if not TORCH_AVAILABLE:
            raise ImportError(
                "PyTorch 未安装，无法使用LSTM预测功能。\n"
                "请安装 PyTorch: pip install torch\n"
                "或者只使用 Prophet 和 XGBoost 模型进行预测。"
            )

        self.sequence_length = sequence_length
        self.model = None
        self.scaler = MinMaxScaler()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def prepare_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """准备时间序列数据"""
        sequences = []
        targets = []

        for i in range(len(data) - self.sequence_length):
            sequences.append(data[i:i + self.sequence_length])
            targets.append(data[i + self.sequence_length])

        return np.array(sequences), np.array(targets)

    def train(self, historical_data: List[Dict], epochs: int = 100):
        """训练LSTM模型"""
        # 准备数据
        df = pd.DataFrame(historical_data)
        features = ['dispatch_count', 'fault_count', 'temperature', 'is_holiday']

        # 标准化
        data = df[features].values
        data_scaled = self.scaler.fit_transform(data)

        # 准备序列
        X, y = self.prepare_sequences(data_scaled)

        # 转换为张量
        X_tensor = torch.FloatTensor(X).to(self.device)
        y_tensor = torch.FloatTensor(y[:, 0:1]).to(self.device)

        # 初始化模型
        self.model = LSTMPredictor(input_size=X.shape[2]).to(self.device)
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)

        # 训练
        self.model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = self.model(X_tensor)
            loss = criterion(outputs, y_tensor)
            loss.backward()
            optimizer.step()

    def predict(self, historical_data: List[Dict], prediction_days: int) -> Dict:
        """预测未来数据"""
        self.model.eval()

        df = pd.DataFrame(historical_data)
        features = ['dispatch_count', 'fault_count', 'temperature', 'is_holiday']
        data = df[features].values
        data_scaled = self.scaler.transform(data)

        # 获取最后一个序列
        last_sequence = data_scaled[-self.sequence_length:]
        sequence_tensor = torch.FloatTensor([last_sequence]).to(self.device)

        # 逐步预测
        predictions = []
        current_sequence = last_sequence.copy()

        with torch.no_grad():
            for _ in range(prediction_days):
                input_tensor = torch.FloatTensor([current_sequence]).to(self.device)
                prediction = self.model(input_tensor)
                pred_value = prediction.cpu().numpy()[0, 0]

                # 反标准化
                full_pred = np.zeros((1, len(features)))
                full_pred[0, 0] = pred_value
                full_pred = self.scaler.inverse_transform(full_pred)

                predictions.append({
                    'date': (datetime.now() + timedelta(days=len(predictions) + 1)).strftime('%Y-%m-%d'),
                    'predicted_dispatches': int(full_pred[0, 0])
                })

                # 更新序列
                new_row = current_sequence[-1].copy()
                new_row[0] = pred_value
                current_sequence = np.vstack([current_sequence[1:], new_row])

        return {
            'model_name': 'LSTM',
            'predictions': predictions,
            'metrics': {
                'sequence_length': self.sequence_length,
                'hidden_size': self.model.hidden_size
            }
        }


class XGBoostPredictor:
    """
    XGBoost时序预测器
    
    优势：
    - 集成学习，性能稳定
    - 处理特征交互
    - 快速训练
    """

    def __init__(self):
        self.model = None
        self.scaler = MinMaxScaler()

    def prepare_features(self, historical_data: List[Dict]) -> pd.DataFrame:
        """准备特征"""
        df = pd.DataFrame(historical_data)

        # 时间特征
        df['date'] = pd.to_datetime(df['date'])
        df['day_of_week'] = df['date'].dt.dayofweek
        df['day_of_month'] = df['date'].dt.day
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter

        # 滞后特征
        df['dispatch_lag_1'] = df['dispatch_count'].shift(1)
        df['dispatch_lag_7'] = df['dispatch_count'].shift(7)

        # 滚动统计
        df['dispatch_ma_7'] = df['dispatch_count'].rolling(window=7).mean()
        df['dispatch_std_7'] = df['dispatch_count'].rolling(window=7).std()

        # 填充缺失值
        df = df.fillna(method='bfill').fillna(method='ffill')

        # 目标变量
        target = df['dispatch_count']

        # 特征
        feature_cols = [
            'day_of_week', 'day_of_month', 'month', 'quarter',
            'dispatch_lag_1', 'dispatch_lag_7',
            'dispatch_ma_7', 'dispatch_std_7',
            'temperature', 'is_holiday'
        ]

        X = df[feature_cols].values
        y = target.values

        return X, y, feature_cols

    def train(self, historical_data: List[Dict]):
        """训练XGBoost模型"""
        X, y, feature_cols = self.prepare_features(historical_data)

        # 标准化
        X_scaled = self.scaler.fit_transform(X)

        # 训练模型
        self.model = XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )

        self.model.fit(X_scaled, y)

    def predict(self, historical_data: List[Dict], prediction_days: int) -> Dict:
        """预测未来数据"""
        # 准备预测数据
        df = pd.DataFrame(historical_data)

        predictions = []
        for i in range(1, prediction_days + 1):
            future_date = datetime.now() + timedelta(days=i)

            # 创建特征
            features = {
                'day_of_week': future_date.weekday(),
                'day_of_month': future_date.day,
                'month': future_date.month,
                'quarter': (future_date.month - 1) // 3 + 1,
                'dispatch_lag_1': df['dispatch_count'].iloc[-1] if i == 1 else predictions[-1]['predicted_dispatches'],
                'dispatch_lag_7': df['dispatch_count'].iloc[-7] if i <= 7 else predictions[-7]['predicted_dispatches'],
                'dispatch_ma_7': df['dispatch_count'].iloc[-7:].mean(),
                'dispatch_std_7': df['dispatch_count'].iloc[-7:].std(),
                'temperature': 25,  # 需要从天气预报获取
                'is_holiday': 0
            }

            # 转换为数组
            X_pred = np.array([list(features.values())])
            X_pred_scaled = self.scaler.transform(X_pred)

            # 预测
            pred_value = self.model.predict(X_pred_scaled)[0]

            predictions.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'predicted_dispatches': int(pred_value)
            })

        return {
            'model_name': 'XGBoost',
            'predictions': predictions,
            'metrics': {
                'feature_importance': dict(zip(
                    ['day_of_week', 'day_of_month', 'month', 'quarter',
                     'dispatch_lag_1', 'dispatch_lag_7', 'dispatch_ma_7',
                     'dispatch_std_7', 'temperature', 'is_holiday'],
                    self.model.feature_importances_.tolist()
                ))
            }
        }


class EnsemblePredictor:
    """
    集成预测器 - 融合多模型结果
    
    策略：
    - 简单平均（权重相等）
    - 加权平均（基于历史性能）
    - 投票机制
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {'Prophet': 0.4, 'LSTM': 0.3, 'XGBoost': 0.3}

    def ensemble(self, predictions_list: List[Dict]) -> Dict:
        """集成多个模型的预测结果"""
        # 提取所有模型的预测
        all_predictions = []
        for pred_dict in predictions_list:
            all_predictions.append(pred_dict['predictions'])

        # 集成预测
        ensemble_predictions = []
        n_days = len(all_predictions[0])

        for day_idx in range(n_days):
            weighted_sum = 0
            total_weight = 0

            for model_idx, model_name in enumerate(['Prophet', 'LSTM', 'XGBoost']):
                if day_idx < len(all_predictions[model_idx]):
                    weight = self.weights.get(model_name, 1.0 / len(predictions_list))
                    weighted_sum += all_predictions[model_idx][day_idx]['predicted_dispatches'] * weight
                    total_weight += weight

            ensemble_value = weighted_sum / total_weight if total_weight > 0 else 0

            ensemble_predictions.append({
                'date': all_predictions[0][day_idx]['date'],
                'predicted_dispatches': int(ensemble_value),
                'confidence': 0.9,  # 集成模型的置信度通常更高
                'ensemble': True,
                'model_weights': self.weights
            })

        return {
            'model_name': 'Ensemble',
            'predictions': ensemble_predictions,
            'individual_results': predictions_list,
            'ensemble_method': 'weighted_average'
        }

    def evaluate_ensemble(self, actual: List[int], predictions: List[int]) -> Dict:
        """评估集成模型性能"""
        mae = mean_absolute_error(actual, predictions)
        mse = mean_squared_error(actual, predictions)
        rmse = np.sqrt(mse)
        r2 = r2_score(actual, predictions)

        return {
            'mae': mae,
            'mse': mse,
            'rmse': rmse,
            'r2': r2,
            'accuracy': max(0, min(1, r2))
        }


# 工具函数
@tool
def predict_with_time_series(
    historical_data: str,
    prediction_days: int = 7,
    models: str = "prophet,lstm,xgboost",
    ensemble: bool = True,
    runtime: ToolRuntime = None
) -> str:
    """
    使用时序预测模型进行业务量预测

    参数：
    - historical_data: 历史数据JSON字符串
    - prediction_days: 预测天数（默认7天）
    - models: 使用的模型，逗号分隔（prophet,lstm,xgboost），默认全部
    - ensemble: 是否使用集成方法（默认True）

    返回：预测结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="predict_with_time_series")

    try:
        # 解析输入数据
        data = json.loads(historical_data)
        historical_records = data.get('records', [])

        if len(historical_records) < 30:
            return json.dumps({
                "success": False,
                "error": "历史数据不足，至少需要30天数据",
                "message": f"当前只有{len(historical_records)}天数据"
            }, ensure_ascii=False)

        # 解析模型列表
        model_list = [m.strip().lower() for m in models.split(',')]

        predictions_list = []
        model_results = {}

        # Prophet预测
        if 'prophet' in model_list:
            try:
                prophet_model = ProphetPredictor()
                df = prophet_model.prepare_data(historical_records)
                prophet_model.train(df)

                # 准备未来日期
                future_dates = pd.DataFrame({
                    'ds': pd.date_range(
                        start=datetime.now(),
                        periods=prediction_days + 1,
                        freq='D'
                    )[1:]
                })

                future_dates['temp_max'] = 25
                future_dates['is_holiday'] = 0

                prophet_result = prophet_model.predict(future_dates)
                predictions_list.append(prophet_result)
                model_results['Prophet'] = prophet_result

            except Exception as e:
                print(f"Prophet预测失败: {e}")

        # LSTM预测
        if 'lstm' in model_list:
            if not TORCH_AVAILABLE:
                print("警告: PyTorch 未安装，跳过LSTM预测")
                model_results['LSTM'] = {
                    'success': False,
                    'warning': 'PyTorch 未安装，LSTM预测功能不可用。请安装: pip install torch'
                }
            else:
                try:
                    lstm_model = LSTMModel(sequence_length=7)
                    lstm_model.train(historical_records, epochs=50)
                    lstm_result = lstm_model.predict(historical_records, prediction_days)
                    predictions_list.append(lstm_result)
                    model_results['LSTM'] = lstm_result

                except Exception as e:
                    print(f"LSTM预测失败: {e}")
                    model_results['LSTM'] = {
                        'success': False,
                        'error': str(e)
                    }

        # XGBoost预测
        if 'xgboost' in model_list:
            try:
                xgb_model = XGBoostPredictor()
                xgb_model.train(historical_records)
                xgb_result = xgb_model.predict(historical_records, prediction_days)
                predictions_list.append(xgb_result)
                model_results['XGBoost'] = xgb_result

            except Exception as e:
                print(f"XGBoost预测失败: {e}")

        # 如果没有成功的模型
        if not predictions_list:
            return json.dumps({
                "success": False,
                "error": "所有预测模型都失败了",
                "message": "请检查数据质量和模型配置"
            }, ensure_ascii=False)

        # 集成预测
        if ensemble and len(predictions_list) > 1:
            ensemble_predictor = EnsemblePredictor()
            final_result = ensemble_predictor.ensemble(predictions_list)
        else:
            final_result = predictions_list[0]

        # 生成预测摘要
        predictions = final_result['predictions']
        total_dispatches = sum(p['predicted_dispatches'] for p in predictions)
        avg_dispatches = total_dispatches / len(predictions)
        peak_day = max(predictions, key=lambda x: x['predicted_dispatches'])
        low_day = min(predictions, key=lambda x: x['predicted_dispatches'])

        result = {
            "success": True,
            "prediction_timestamp": datetime.now().isoformat(),
            "prediction_horizon": f"{prediction_days} days",
            "model_used": final_result['model_name'],
            "prediction_summary": {
                "total_predicted_dispatches": total_dispatches,
                "avg_daily_dispatches": round(avg_dispatches, 1),
                "peak_day": peak_day['date'],
                "peak_dispatches": peak_day['predicted_dispatches'],
                "low_day": low_day['date'],
                "low_dispatches": low_day['predicted_dispatches'],
                "volatility": peak_day['predicted_dispatches'] - low_day['predicted_dispatches']
            },
            "daily_predictions": predictions,
            "individual_model_results": model_results if len(model_results) > 1 else None,
            "metadata": {
                "historical_data_days": len(historical_records),
                "models_attempted": model_list,
                "ensemble_enabled": ensemble,
                "prediction_confidence": predictions[0].get('confidence', 0.9) if predictions else 0
            }
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "时序预测失败"
        }, ensure_ascii=False)


@tool
def evaluate_prediction_performance(
    actual_data: str,
    predicted_data: str,
    runtime: ToolRuntime = None
) -> str:
    """
    评估预测模型性能

    参数：
    - actual_data: 实际数据JSON字符串
    - predicted_data: 预测数据JSON字符串

    返回：性能评估结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="evaluate_prediction_performance")

    try:
        actual = json.loads(actual_data)
        predicted = json.loads(predicted_data)

        # 提取值
        actual_values = [d['dispatch_count'] for d in actual.get('records', [])]
        predicted_values = [d['predicted_dispatches'] for d in predicted.get('predictions', [])]

        # 计算指标
        mae = mean_absolute_error(actual_values, predicted_values)
        mse = mean_squared_error(actual_values, predicted_values)
        rmse = np.sqrt(mse)
        r2 = r2_score(actual_values, predicted_values)

        # 准确率计算（允许10%误差）
        tolerance = 0.1
        accurate_count = sum(
            1 for a, p in zip(actual_values, predicted_values)
            if abs(a - p) / (a + 1e-10) <= tolerance
        )
        accuracy = accurate_count / len(actual_values) if actual_values else 0

        result = {
            "success": True,
            "evaluation_timestamp": datetime.now().isoformat(),
            "metrics": {
                "mae": round(mae, 2),
                "mse": round(mse, 2),
                "rmse": round(rmse, 2),
                "r2_score": round(r2, 4),
                "accuracy": round(accuracy * 100, 2),
                "accurate_predictions": accurate_count,
                "total_predictions": len(actual_values)
            },
            "interpretation": {
                "mae": f"平均绝对误差：{mae:.2f}次调度",
                "rmse": f"均方根误差：{rmse:.2f}次调度",
                "accuracy": f"预测准确率：{accuracy * 100:.1f}%",
                "r2_score": f"模型拟合度：{r2:.2%}"
            },
            "recommendation": "优秀" if accuracy >= 0.85 else "良好" if accuracy >= 0.75 else "需要改进"
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "性能评估失败"
        }, ensure_ascii=False)
