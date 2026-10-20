import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import LabelEncoder
import warnings
import os
import glob
warnings.filterwarnings("ignore", category=UserWarning)

def adjust_predictions_temporal(predictions, protect_strategy='top_percent', protect_param=20):
    pred = np.array(predictions, dtype=float)
    original_sum = pred.sum()
    
    # 边界检查
    if original_sum <= 0:
        return np.maximum(pred, 0)
    
    # 1. 计算补偿量：每个负数-a→+a需要增加2a的总量
    neg_mask = pred < 0
    compensation = 2 * np.abs(pred[neg_mask]).sum()
    
    if compensation == 0:
        return pred  # 无负数，无需调整
    
    # 2. 识别需要保护的极大值位置
    pos_values = pred[~neg_mask]
    if len(pos_values) == 0:
        return adjust_fallback(pred)  # 全是负数
    
    # 根据策略选择保护位置
    if protect_strategy == 'top_n':
        n_protect = min(int(protect_param), len(pos_values))
        protect_threshold = np.partition(pos_values, -n_protect)[-n_protect]
        
    elif protect_strategy == 'top_percent':
        percent = np.clip(protect_param, 0, 100) / 100
        n_protect = max(1, int(len(pos_values) * percent))
        protect_threshold = np.partition(pos_values, -n_protect)[-n_protect]
        
    elif protect_strategy == 'threshold':
        protect_threshold = protect_param
        n_protect = np.sum(pos_values >= protect_threshold)
        
    else:
        raise ValueError("protect_strategy必须是 'top_n', 'top_percent' 或 'threshold'")
    
    # 创建保护掩码（极大值且为正数）
    protect_mask = (pred >= protect_threshold) & (~neg_mask)
    n_protect = protect_mask.sum()
    
    # 3. 分级调整策略
    non_protect_mask = (~neg_mask) & (~protect_mask)
    non_protect_sum = pred[non_protect_mask].sum()
    
    if compensation < non_protect_sum:
        # 【理想情况】补偿量较小，只调整非极大值
        adjusted = pred.copy()
        # 非极大值按比例缩小
        deduction_ratio = compensation / non_protect_sum
        adjusted[non_protect_mask] *= (1 - deduction_ratio)
        # 极大值数量保持不变
        # 负数转正
        adjusted[neg_mask] = np.abs(pred[neg_mask])
        
    else:
        # 【极端情况】补偿量过大，极大值也需参与调整
        print(f"补偿量({compensation:.2f})超过非极大值总额({non_protect_sum:.2f})")
        print(f"极大值也需减少，但保持相对大小关系")
        
        adjusted = pred.copy()
        
        if non_protect_sum > 0:
            # 非极大值先承担70%（可调整比例）
            first_deduction = min(compensation * 0.7, non_protect_sum)
            deduction_ratio = first_deduction / non_protect_sum
            adjusted[non_protect_mask] *= (1 - deduction_ratio)
            remaining_compensation = compensation - first_deduction
        else:
            remaining_compensation = compensation
        
        # 极大值承担剩余部分（按值大小权重分配）
        protect_sum = pred[protect_mask].sum()
        if protect_sum > remaining_compensation:
            deduction_ratio_protect = remaining_compensation / protect_sum
            adjusted[protect_mask] *= (1 - deduction_ratio_protect)
        else:
            adjusted[protect_mask] = 0
        
        # 负数转正
        adjusted[neg_mask] = np.abs(pred[neg_mask])
    
    # 4. 微调整确保总和精确守恒
    adjusted *= (original_sum / adjusted.sum())
    
    return adjusted

def date_feature_engineering(df):
    df['月份'] = pd.to_datetime(df['月份'])
    df['Year'] = df['月份'].dt.year
    df['Quarter'] = df['月份'].dt.quarter
    df['Month'] = df['月份'].dt.month
    df['Day'] = df['月份'].dt.day
    df['day_of_week'] = df['月份'].dt.dayofweek
    df['week'] = df['月份'].dt.isocalendar().week
    df['week_of_year'] = df['月份'].dt.isocalendar().week
    # Cyclical Features
    df['day_sin'] = np.sin(2 * np.pi * df['Day'] / 365.0)
    df['day_cos'] = np.cos(2 * np.pi * df['Day'] / 365.0)
    df['week_sin'] = np.sin(df['week'] * (2 * np.pi/ 53))
    df['week_cos'] = np.cos(df['week'] * (2 * np.pi/ 53))
    df['month_sin'] = np.sin(2 * np.pi * df['Month'] / 12.0)
    df['month_cos'] = np.cos(2 * np.pi * df['Month'] / 12.0)
    df['year_sin'] = np.sin(2 * np.pi * df['Year'] / 7.0)
    df['year_cos'] = np.cos(2 * np.pi * df['Year'] / 7.0)
    return df

def read_file_model(month, sales_target=0, max_subsidy=0, ecom_policy=0):
    # model = tf.keras.models.load_model('./bingo_2026_'+str(month)+'/bingo_2026_'+str(month)+'_18.keras')
    # df = pd.read_excel('./bingo_2026_'+str(month)+'/bingo.xlsx', engine='openpyxl')
    base_path = f'./bingo_2026_{month}'

    if not os.path.exists(base_path):
        # 获取所有 bingo_2026_* 文件夹
        folders = [f for f in glob.glob('./bingo_2026_*') if os.path.isdir(f)]
        if not folders:
            raise FileNotFoundError("No bingo_2026_* folders found.")
        base_path = max(folders, key=lambda x: int(x.split('_')[-1]))

    month_str = base_path.split('_')[-1]
    model = tf.keras.models.load_model(f'{base_path}/bingo_2026_{month_str}_18.keras')
    df = pd.read_excel(f'{base_path}/bingo.xlsx', engine='openpyxl')
    print(f'{base_path}/bingo.xlsx')

    df = df.drop(columns=["星期"])
    df = date_feature_engineering(df)
    df = df.drop(columns=["月份", "销量"])
    df['week'] = df['week'].astype('float')
    df['week_of_year'] = df['week_of_year'].astype('float')

    df['汽车消费补贴政策'] = df['汽车消费补贴政策'].fillna(0)
    
    non_empty_indices = df.dropna(subset=['人均收入']).index
    start_row1 = 0
    end_row1 = 90
    df.loc[0, '人均收入'] = 0.0
    df.loc[start_row1:end_row1, '人均收入'] = df.loc[start_row1:end_row1, '人均收入'].interpolate(method='linear')

    df.loc[90: 181, '人均收入'] = df.loc[90: 181, '人均收入'].interpolate(method='linear')
    df.loc[181: 273, '人均收入'] = df.loc[181: 273, '人均收入'].interpolate(method='linear')
    df.loc[273: 365, '人均收入'] = df.loc[273: 365, '人均收入'].interpolate(method='linear')

    df.loc[366, '人均收入'] = 0.0
    df.loc[366: 455, '人均收入'] = df.loc[366: 455, '人均收入'].interpolate(method='linear')
    df.loc[455: 546, '人均收入'] = df.loc[455: 546, '人均收入'].interpolate(method='linear')
    df.loc[546: 638, '人均收入'] = df.loc[546: 638, '人均收入'].interpolate(method='linear')
    df.loc[638: 730, '人均收入'] = df.loc[638: 730, '人均收入'].interpolate(method='linear')

    df.loc[731, '人均收入'] = 0.0
    # # 243（8月），273（9月），304（10月），334（11月），365（12月）
    increase_percentage = (df.loc[455, '人均收入']/90)*1.05 
    for i in range(732, len(df)):
        df.loc[i, '人均收入'] = df.loc[i-1, '人均收入'] + increase_percentage

    df['汽车消费补贴政策'] = df['汽车消费补贴政策'].fillna(0)
    df['消费者信心指数'] = df['消费者信心指数'].fillna(df['消费者信心指数'].mean())
    # df['消费者信心指数'] = df['消费者信心指数'].fillna(88)
    df['PMI'] = df['PMI'].fillna(df['PMI'].mean())
    df['工业生产者出厂价格指数'] = df['工业生产者出厂价格指数'].fillna(df['工业生产者出厂价格指数'].min())
    if month == 1:
        df['汽车消费指数'] = df['汽车消费指数'].fillna(50)
        df['汽车消费指数-需求分指数'] = df['汽车消费指数-需求分指数'].fillna(48.5)
    if month == 2:
        df['汽车消费指数'] = df['汽车消费指数'].fillna(75)
        df['汽车消费指数-需求分指数'] = df['汽车消费指数-需求分指数'].fillna(70.5)
    if month == 3:
        df['汽车消费指数'] = df['汽车消费指数'].fillna(80)
        df['汽车消费指数-需求分指数'] = df['汽车消费指数-需求分指数'].fillna(78.5)

    target = 'invoicing_count'
    features = df.drop(columns=[target]).columns
    categorical_features = ['节假日', '年干', '年支', '月干', '月支', '日干', '日支']
    numerical_features = [col for col in features if col not in categorical_features]
    
    label_encoders = {}
    for feature in categorical_features:
        le = LabelEncoder()
        df[feature] = le.fit_transform(df[feature])
        label_encoders[feature] = le

    X = df.drop(columns=[target])
    y = df[target]

    if month == 1:
        X_test = X[731: 762]
    X_test_dict = {col: X_test[col].values for col in X_test.columns}
    features = df.drop(columns=['invoicing_count'])
    if month == 1:
        X_test_line = features[731: 762]

    if sales_target != 0:
        X_test['月销量目标'] = sales_target
        X_test_line['月销量目标'] = sales_target
    if max_subsidy != 0:
        X_test['实销支持/优惠券'] = max_subsidy
        X_test_line['实销支持/优惠券'] = max_subsidy
    if ecom_policy != 0:
        X_test['电商活动'] = ecom_policy
        X_test_line['电商活动'] = ecom_policy
    
    X_test_dict = {col: X_test[col].values for col in X_test.columns}
    X_test_inputs = [X_test_dict[col] for col in categorical_features + numerical_features]
    test_inputs = [X_test_line, X_test_line, X_test_line, X_test_line] + X_test_inputs
    
    return model, test_inputs

def predict_month(month, sales_target=0, max_subsidy=0, ecom_policy=0):
    model, test_inputs = read_file_model(month, sales_target=0, max_subsidy=0, ecom_policy=0)
    return adjust_predictions_temporal(model.predict(test_inputs))

month = 12

predict_month(month).sum()