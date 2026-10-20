import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import LabelEncoder
import warnings
import os
import glob

warnings.filterwarnings("ignore", category=UserWarning)

def adjust_predictions_flexible_negative(predictions, base_value=1.0, sensitivity=0.5, cap_value=30.0):
    pred = np.array(predictions, dtype=float)
    original_sum = pred.sum()
    if original_sum <= 0:
        return np.full_like(pred, max(base_value, original_sum / len(pred)))

    neg_mask = pred < 0
    if not np.any(neg_mask):
        return pred
        
    neg_values = pred[neg_mask]
    abs_neg = np.abs(neg_values)
    flexible_targets = base_value + sensitivity * np.sqrt(abs_neg)
    flexible_targets = np.minimum(flexible_targets, cap_value)
    deficit = np.sum(flexible_targets - neg_values)
    pos_mask = pred > 0
    current_pos_sum = pred[pos_mask].sum()
    if current_pos_sum <= deficit:
        avg_val = original_sum / len(pred)
        return np.full_like(pred, max(avg_val, base_value))
    
    corrected_neg_sum = np.sum(flexible_targets)
    target_pos_sum = original_sum - corrected_neg_sum
    scale_factor = target_pos_sum / current_pos_sum
    adjusted = pred.copy()
    adjusted[neg_mask] = flexible_targets
    adjusted[pos_mask] *= scale_factor
    current_total = adjusted.sum()
    if not np.isclose(current_total, original_sum):
        final_scale = original_sum / current_total
        adjusted *= final_scale
        if np.any(adjusted[neg_mask] < base_value * 0.9): 
             adjusted[adjusted < base_value * 0.5] = base_value * 0.5
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

def read_file_model(year, month, sales_target=0, max_subsidy=0, ecom_policy=0):
    # 构建基础路径：例如 ./2025_10
    actual_month = str(int(month)).zfill(2)
    base_path = f'./{year}_{actual_month}'
    print(base_path)

    # 重新解析实际使用的年份和月份（以防自动切换了）
    parts = os.path.basename(base_path).split('_')
    actual_year = str(parts[0])
    actual_month = str(int(parts[1])).zfill(2)
    
    # 构造模型和Excel文件名
    model_filename = f'bingo_{actual_year}_{actual_month}_18.keras'
    data_filename = 'bingo.xlsx'
    
    model_path = os.path.join(base_path, model_filename)
    data_path = os.path.join(base_path, data_filename)
    
    if not os.path.exists(model_path):
        folders = [f for f in glob.glob('./*') if os.path.isdir(f)]
        import re
        date_folders = [f for f in folders if re.match(r'^\./\d{4}_\d{2}$', f)]
        base_path = max(date_folders)
        model_pattern = os.path.join(base_path, '*.keras') # 匹配所有 keras 文件
        files = glob.glob(model_pattern)
        model_path = max(files, key=os.path.getmtime)
            
    if not os.path.exists(data_path):
         data_path = './bingo.xlsx'
        
    df = pd.read_excel(data_path, engine='openpyxl')
    df['经销商支持'] = df['经销商支持'].fillna(0)
    # zhengce = pd.read_excel('./zhengce.xlsx', engine='openpyxl',)
    # for i in range(len(zhengce)):
    #     start = zhengce['开始日期'].iloc[i]
    #     end = zhengce['结束日期'].iloc[i]
    #     mask = (df['月份'] >= start) & (df['月份'] <= end)
    #     df.loc[mask, '经销商支持'] = df.loc[mask, '经销商支持'] + 1   

    df = df.drop(columns=["星期", "销量"])
    df = date_feature_engineering(df)
    df = df.drop(columns=["月份"])
    df['week'] = df['week'].astype('float')
    df['week_of_year'] = df['week_of_year'].astype('float')

    df.loc[0, '人均收入'] = 0.0
    df.loc[0: 90, '人均收入'] = df.loc[0: 90, '人均收入'].interpolate(method='linear')
    df.loc[90: 181, '人均收入'] = df.loc[90: 181, '人均收入'].interpolate(method='linear')
    df.loc[181: 273, '人均收入'] = df.loc[181: 273, '人均收入'].interpolate(method='linear')
    df.loc[273: 365, '人均收入'] = df.loc[273: 365, '人均收入'].interpolate(method='linear')

    df.loc[366, '人均收入'] = 0.0
    df.loc[366: 455, '人均收入'] = df.loc[366: 455, '人均收入'].interpolate(method='linear')
    if year == 2025:
        if month == 6:
            increase_percentage = df.loc[455, '人均收入']/89
            for i in range(456, len(df)):
                df.loc[i, '人均收入'] = df.loc[i-1, '人均收入'] + increase_percentage
        if (month == 7) or (month == 8) or (month == 9):
            df.loc[455: 546, '人均收入'] = df.loc[455: 546, '人均收入'].interpolate(method='linear')
            increase_percentage = df.loc[546, '人均收入']/180
            for i in range(547, len(df)):
                df.loc[i, '人均收入'] = df.loc[i-1, '人均收入'] + increase_percentage
        if (month == 10) or (month == 11) or (month == 12):
            df.loc[455: 546, '人均收入'] = df.loc[455: 546, '人均收入'].interpolate(method='linear')
            df.loc[546: 638, '人均收入'] = df.loc[546: 638, '人均收入'].interpolate(method='linear')
            increase_percentage = df.loc[638, '人均收入']/273
            for i in range(639, len(df)):
                df.loc[i, '人均收入'] = df.loc[i-1, '人均收入'] + increase_percentage
    if year == 2026:
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

    fill_config = pd.read_excel('fill_config.xlsx', engine='openpyxl')
    mask = (fill_config['年份'] == year) & (fill_config['月份'] == month)
    result = fill_config[mask]
    df.loc[int(result.iloc[0, 4]): int(result.iloc[0, 5]), '汽车消费指数'] = result.iloc[0, 2]
    df.loc[int(result.iloc[0, 4]): int(result.iloc[0, 5]), '汽车消费指数-需求分指数'] = result.iloc[0, 3]
    df = df.ffill()
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
    X_test = X[int(result.iloc[0, 4]): int(result.iloc[0, 5])]
    # print(X_test)
    X_test_dict = {col: X_test[col].values for col in X_test.columns}
    features = df.drop(columns=['invoicing_count'])
    X_test_line = features[int(result.iloc[0, 4]): int(result.iloc[0, 5])]
    
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
    
    model = tf.keras.models.load_model(model_path)
    return model, test_inputs

def predict_month(year, month, sales_target=0, max_subsidy=0, ecom_policy=0):
    print(year, month)
    model, test_inputs = read_file_model(year, month, sales_target, max_subsidy, ecom_policy)
    predictions = model.predict(test_inputs)
    return adjust_predictions_flexible_negative(predictions)

input_year = 2026
input_month = 7
result = predict_month(input_year, input_month)
result.sum()