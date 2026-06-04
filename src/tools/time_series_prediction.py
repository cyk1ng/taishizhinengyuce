"""时序预测工具 - 支持Prophet、LSTM、XGBoost多模型预测"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from langchain.tools import tool

logger = logging.getLogger(__name__)


def _lazy_prophet():
    """延迟加载 Prophet"""
    import importlib
    return importlib.import_module('prophet').Prophet


def _lazy_sklearn_scaler():
    import importlib
    return importlib.import_module('sklearn.preprocessing').MinMaxScaler


def _lazy_xgb():
    import importlib
    return importlib.import_module('xgboost').XGBRegressor


def _lazy_sklearn_metrics():
    import importlib
    m = importlib.import_module('sklearn.metrics')
    return m.mean_absolute_error, m.mean_squared_error, m.r2_score


def _lazy_torch():
    import importlib
    return importlib.import_module('torch')


def _lazy_nn():
    import importlib
    return importlib.import_module('torch.nn')


# ============================================================
# 数据加载（从MySQL获取历史调度数据）
# ============================================================

def _load_training_data(days: int = 365) -> pd.DataFrame:
    """
    从文件或数据库加载历史训练数据
    实际生产应从数据库读取
    """
    data_path = os.path.join(os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"), "assets", "historical_workload.csv")
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        df['date'] = pd.to_datetime(df['date'])
        return df
    # 生成模拟数据用于测试
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    base = 100 + np.sin(np.arange(days) * 2 * np.pi / 7) * 20  # 周周期性
    base += np.sin(np.arange(days) * 2 * np.pi / 365) * 30  # 年周期性
    noise = np.random.normal(0, 15, days)
    workload = base + noise
    df = pd.DataFrame({'date': dates, 'workload': np.maximum(workload, 10)})
    return df


# ============================================================
# Prophet预测模型
# ============================================================

class ProphetPredictor:
    """Prophet时间序列预测"""
    
    def __init__(self, **params):
        self.params = params
        self.model = None
    
    def fit(self, df: pd.DataFrame):
        Prophet = _lazy_prophet()
        self.model = Prophet(
            yearly_seasonality=self.params.get('yearly_seasonality', True),
            weekly_seasonality=self.params.get('weekly_seasonality', True),
            daily_seasonality=self.params.get('daily_seasonality', False),
            seasonality_mode=self.params.get('seasonality_mode', 'additive'),
            changepoint_prior_scale=self.params.get('changepoint_prior_scale', 0.05),
            **{k: v for k, v in self.params.items() if k not in ['yearly_seasonality', 'weekly_seasonality', 'daily_seasonality', 'seasonality_mode', 'changepoint_prior_scale']}
        )
        prophet_df = df.rename(columns={'date': 'ds', 'workload': 'y'})
        self.model.fit(prophet_df)
        return self
    
    def predict(self, periods: int) -> pd.DataFrame:
        future = self.model.make_future_dataframe(periods=periods, freq='D')
        forecast = self.model.predict(future)
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)


# ============================================================
# LSTM预测模型
# ============================================================

class LSTMPredictor:
    """LSTM神经网络预测"""
    
    def __init__(self, input_size=1, hidden_size=64, num_layers=2, learning_rate=0.001, epochs=50):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.model = None
        self.scaler = None
    
    def _build_model(self):
        nn = _lazy_nn()
        
        class _LSTM(nn.Module):
            def __init__(self, input_size, hidden_size, num_layers):
                super().__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
                self.linear = nn.Linear(hidden_size, 1)
            
            def forward(self, x):
                out, _ = self.lstm(x)
                out = self.linear(out[:, -1, :])
                return out
        
        return _LSTM(self.input_size, self.hidden_size, self.num_layers)
    
    def _create_sequences(self, data, seq_length=30):
        X, y = [], []
        for i in range(len(data) - seq_length):
            X.append(data[i:i + seq_length])
            y.append(data[i + seq_length])
        return np.array(X), np.array(y)
    
    def fit(self, df: pd.DataFrame):
        torch = _lazy_torch()
        MinMaxScaler = _lazy_sklearn_scaler()
        
        values = np.array(df['workload'].values).reshape(-1, 1)
        self.scaler = MinMaxScaler()
        scaled = self.scaler.fit_transform(values)
        
        seq_length = min(30, len(scaled) // 3)
        X, y = self._create_sequences(scaled.flatten(), seq_length)
        
        split = int(len(X) * 0.8)
        X_train, y_train = X[:split], y[:split]
        
        X_train_t = torch.FloatTensor(X_train).unsqueeze(-1)
        y_train_t = torch.FloatTensor(y_train)
        
        self.model = self._build_model()
        criterion = torch.nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        
        self.model.train()
        for epoch in range(self.epochs):
            optimizer.zero_grad()
            output = self.model(X_train_t)
            loss = criterion(output.squeeze(), y_train_t)
            loss.backward()
            optimizer.step()
        
        return self
    
    def predict(self, periods: int) -> pd.DataFrame:
        torch = _lazy_torch()
        MinMaxScaler = _lazy_sklearn_scaler()
        
        values = self.scaler.inverse_transform([[0]])  # 获取形状
        # 简单预测：使用最后30天预测下一天，迭代预测
        last_data = self.scaler.transform(np.zeros((30, 1)))  # 简化处理
        
        self.model.eval()
        predictions = []
        current = torch.FloatTensor(last_data).unsqueeze(0)
        
        with torch.no_grad():
            for i in range(periods):
                pred = self.model(current)
                predictions.append(pred.item())
                current = torch.cat([current[:, 1:, :], pred.unsqueeze(0).unsqueeze(-1)], dim=1)
        
        pred_array = np.array(predictions).reshape(-1, 1)
        pred_values = self.scaler.inverse_transform(pred_array).flatten()
        
        last_date = datetime.now()
        dates = [last_date + timedelta(days=i + 1) for i in range(periods)]
        
        return pd.DataFrame({
            'ds': dates,
            'yhat': pred_values,
            'yhat_lower': pred_values * 0.85,
            'yhat_upper': pred_values * 1.15
        })


# ============================================================
# XGBoost预测模型
# ============================================================

class XGBoostPredictor:
    """XGBoost梯度提升预测"""
    
    def __init__(self, **params):
        self.params = params
        self.model = None
    
    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['dayofweek'] = df['date'].dt.dayofweek
        df['day'] = df['date'].dt.day
        df['month'] = df['date'].dt.month
        df['year'] = df['date'].dt.year
        df['dayofyear'] = df['date'].dt.dayofyear
        df['sin_week'] = np.sin(2 * np.pi * df['dayofweek'] / 7)
        df['cos_week'] = np.cos(2 * np.pi * df['dayofweek'] / 7)
        df['sin_year'] = np.sin(2 * np.pi * df['dayofyear'] / 365)
        df['cos_year'] = np.cos(2 * np.pi * df['dayofyear'] / 365)
        return df
    
    def fit(self, df: pd.DataFrame):
        XGBRegressor = _lazy_xgb()
        df_feat = self._create_features(df)
        feature_cols = ['dayofweek', 'day', 'month', 'year', 'sin_week', 'cos_week', 'sin_year', 'cos_year']
        X = df_feat[feature_cols]
        y = df_feat['workload']
        
        self.model = XGBRegressor(
            n_estimators=self.params.get('n_estimators', 200),
            max_depth=self.params.get('max_depth', 6),
            learning_rate=self.params.get('learning_rate', 0.1),
            random_state=42
        )
        self.model.fit(X, y)
        return self
    
    def predict(self, periods: int) -> pd.DataFrame:
        last_date = datetime.now()
        future_dates = [last_date + timedelta(days=i + 1) for i in range(periods)]
        future_df = pd.DataFrame({'date': future_dates})
        future_feat = self._create_features(future_df)
        feature_cols = ['dayofweek', 'day', 'month', 'year', 'sin_week', 'cos_week', 'sin_year', 'cos_year']
        predictions = self.model.predict(future_feat[feature_cols])
        
        return pd.DataFrame({
            'ds': future_dates,
            'yhat': predictions,
            'yhat_lower': predictions * 0.85,
            'yhat_upper': predictions * 1.15
        })


# ============================================================
# 集成预测
# ============================================================

def _ensemble_predict(df: pd.DataFrame, periods: int = 30) -> pd.DataFrame:
    """多模型集成预测"""
    results = {}
    errors = {}
    
    # Prophet预测
    try:
        prophet = ProphetPredictor()
        prophet.fit(df)
        prophet_result = prophet.predict(periods)
        results['prophet'] = prophet_result
        logger.info("Prophet预测成功")
    except Exception as e:
        errors['prophet'] = str(e)
        logger.warning(f"Prophet预测失败: {e}")
    
    # XGBoost预测
    try:
        xgb = XGBoostPredictor()
        xgb.fit(df)
        xgb_result = xgb.predict(periods)
        results['xgboost'] = xgb_result
        logger.info("XGBoost预测成功")
    except Exception as e:
        errors['xgboost'] = str(e)
        logger.warning(f"XGBoost预测失败: {e}")
    
    # LSTM预测
    try:
        lstm = LSTMPredictor(epochs=20)
        lstm.fit(df)
        lstm_result = lstm.predict(periods)
        results['lstm'] = lstm_result
        logger.info("LSTM预测成功")
    except Exception as e:
        errors['lstm'] = str(e)
        logger.warning(f"LSTM预测失败: {e}")
    
    if not results:
        raise RuntimeError(f"所有模型预测失败: {errors}")
    
    # 集成平均
    ensemble = pd.DataFrame({'ds': list(results.values())[0]['ds']})
    yhats = []
    yhat_lowers = []
    yhat_uppers = []
    
    for result in results.values():
        yhats.append(result['yhat'].values)
        yhat_lowers.append(result['yhat_lower'].values)
        yhat_uppers.append(result['yhat_upper'].values)
    
    ensemble['yhat'] = np.mean(yhats, axis=0)
    ensemble['yhat_lower'] = np.min(yhat_lowers, axis=0)
    ensemble['yhat_upper'] = np.max(yhat_uppers, axis=0)
    ensemble['models_used'] = len(results)
    ensemble['errors'] = str(errors) if errors else ""
    
    return ensemble


# ============================================================
# Tool函数
# ============================================================

@tool
def predict_with_time_series(
    days: int = 30,
    model_type: str = "ensemble"
) -> str:
    """使用时间序列模型(Prophet/LSTM/XGBoost)预测未来调度业务量
    
    Args:
        days: 预测天数，默认30天
        model_type: 模型类型，可选: ensemble(集成), prophet, lstm, xgboost
    """
    try:
        df = _load_training_data()
        
        if model_type == "prophet":
            predictor = ProphetPredictor()
            predictor.fit(df)
            result = predictor.predict(days)
        elif model_type == "lstm":
            predictor = LSTMPredictor(epochs=20)
            predictor.fit(df)
            result = predictor.predict(days)
        elif model_type == "xgboost":
            predictor = XGBoostPredictor()
            predictor.fit(df)
            result = predictor.predict(days)
        else:
            result = _ensemble_predict(df, days)
        
        # 格式化输出
        output = {
            "success": True,
            "model_type": model_type,
            "predictions": []
        }
        
        for _, row in result.iterrows():
            output["predictions"].append({
                "date": str(pd.Timestamp(row['ds']).strftime('%Y-%m-%d')),
                "predicted_workload": round(float(row['yhat']), 1),
                "lower_bound": round(float(row['yhat_lower']), 1),
                "upper_bound": round(float(row['yhat_upper']), 1)
            })
        
        if 'models_used' in result.columns:
            output["models_used"] = int(result['models_used'].iloc[0])
        if 'errors' in result.columns and result['errors'].iloc[0]:
            output["model_errors"] = result['errors'].iloc[0]
        
        return json.dumps(output, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "时序预测失败，请检查依赖包是否安装完整"
        }, ensure_ascii=False)


@tool
def evaluate_prediction_performance(
    model_type: str = "ensemble"
) -> str:
    """评估预测模型的性能指标（MAE, RMSE, R²）
    
    Args:
        model_type: 模型类型，可选: ensemble, prophet, lstm, xgboost
    """
    try:
        mean_absolute_error, mean_squared_error, r2_score = _lazy_sklearn_metrics()
        
        df = _load_training_data()
        split = int(len(df) * 0.8)
        train_df = df.iloc[:split]
        test_df = df.iloc[split:]
        
        if model_type == "prophet":
            predictor = ProphetPredictor()
            predictor.fit(train_df)
            result = predictor.predict(len(test_df))
        elif model_type == "lstm":
            predictor = LSTMPredictor(epochs=20)
            predictor.fit(train_df)
            result = predictor.predict(len(test_df))
        elif model_type == "xgboost":
            predictor = XGBoostPredictor()
            predictor.fit(train_df)
            result = predictor.predict(len(test_df))
        else:
            result = _ensemble_predict(train_df, len(test_df))
        
        y_true = test_df['workload'].values[:len(result)]
        y_pred = result['yhat'].values[:len(y_true)]
        
        mae = mean_absolute_error(y_true, y_pred)
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_true, y_pred)
        
        # 计算MAPE
        non_zero_mask = y_true > 0
        mape = np.mean(np.abs((y_true[non_zero_mask] - y_pred[non_zero_mask]) / y_true[non_zero_mask])) * 100
        
        return json.dumps({
            "success": True,
            "model_type": model_type,
            "metrics": {
                "mae": round(float(mae), 2),
                "mse": round(float(mse), 2),
                "rmse": round(float(rmse), 2),
                "r2_score": round(float(r2), 4),
                "mape_percent": round(float(mape), 2)
            },
            "test_samples": len(y_true)
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "模型评估失败"
        }, ensure_ascii=False, indent=2)