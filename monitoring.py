"""Synthetic banking data and auditable monitoring rules (Python 3.9)."""
from dataclasses import dataclass
from datetime import datetime, timedelta
import math
import random

import pandas as pd


@dataclass(frozen=True)
class Thresholds:
    large_amount: float = 5000.0
    frequency_count: int = 5
    window_minutes: int = 60
    flag_score: int = 35
    relative_multiplier: float = 4.0
    min_history: int = 5

    def validate(self):
        if not math.isfinite(self.large_amount) or self.large_amount <= 0:
            raise ValueError('Large-amount threshold must be positive and finite.')
        if not isinstance(self.frequency_count, int) or not isinstance(self.window_minutes, int) or self.frequency_count < 2 or self.window_minutes < 1:
            raise ValueError('Frequency count must be at least 2 and window at least 1 minute.')
        if not math.isfinite(self.relative_multiplier) or self.relative_multiplier <= 1:
            raise ValueError('Relative multiplier must be finite and greater than 1.')
        if not isinstance(self.min_history, int) or self.min_history < 1:
            raise ValueError('Minimum history must be a positive integer.')
        if not 1 <= self.flag_score <= 100:
            raise ValueError('Flag score must be between 1 and 100.')


def generate_transactions(count=500, seed=9):
    """Create reproducible fictional records, including large amounts and bursts."""
    if not isinstance(count, int) or count < 500:
        raise ValueError('Generate at least 500 transactions.')
    rng = random.Random(seed)
    start = datetime(2025, 1, 1)
    rows = []
    for i in range(count):
        rows.append({
            'transaction_id': 'TX{:05d}'.format(i + 1),
            'timestamp': start + timedelta(minutes=rng.randrange(30 * 24 * 60)),
            'account_id': 'AC{:03d}'.format(rng.randrange(1, 31)),
            'amount': round(min(rng.lognormvariate(5.6, 1.0), 4500), 2),
            'direction': rng.choices(['Debit', 'Credit'], weights=[85, 15])[0],
            'channel': rng.choice(['Card', 'Transfer', 'ATM', 'Online']),
            'category': rng.choice(['Retail', 'Bills', 'Travel', 'Income', 'Other']),
        })
    for i in range(8):
        rows[i]['amount'] = round(rng.uniform(8000, 25000), 2)
    for i in range(8, 20):
        rows[i].update(account_id='AC001', timestamp=start + timedelta(days=15, minutes=i - 8),
                       amount=round(rng.uniform(600, 1500), 2), direction='Debit', channel='Transfer')
    data = pd.DataFrame(rows).sort_values(['timestamp', 'transaction_id']).reset_index(drop=True)
    data['customer_id'] = data['account_id'].str.replace('AC', 'CU', regex=False)
    data.loc[data['direction'] == 'Credit', 'category'] = 'Income'
    data['scenario'] = 'Routine activity'
    data.loc[data.transaction_id.isin(['TX{:05d}'.format(i) for i in range(1, 9)]), 'scenario'] = 'Planted large amount'
    data.loc[data.transaction_id.isin(['TX{:05d}'.format(i) for i in range(9, 21)]), 'scenario'] = 'Planted activity burst'
    signed = data['amount'].where(data['direction'] == 'Credit', -data['amount'])
    # An illustrative credit facility permits negative balances; no overdraft rule.
    data['account_balance'] = (50000 + signed.groupby(data['account_id']).cumsum()).round(2)
    return data


def score_transactions(frame, thresholds=None):
    """Score all records using a trailing per-customer window inclusive of current record.

    Equal timestamps include all simultaneous records, making results independent
    of input order. No later timestamp contributes to a transaction's score.
    """
    config = thresholds or Thresholds()
    config.validate()
    required = {'transaction_id', 'timestamp', 'account_id', 'amount', 'direction', 'channel', 'category'}
    if not required.issubset(frame.columns):
        raise ValueError('Missing required columns: ' + ', '.join(sorted(required - set(frame.columns))))
    data = frame.copy()
    if data.empty:
        raise ValueError('No transactions to analyze.')
    if data[list(required)].isna().any().any() or any(data[col].astype(str).str.strip().eq('').any() for col in required):
        raise ValueError('Transaction fields cannot be empty.')
    data['timestamp'] = pd.to_datetime(data['timestamp'], errors='coerce', utc=True)
    data['amount'] = pd.to_numeric(data['amount'], errors='coerce')
    if data['timestamp'].isna().any() or not data['amount'].map(lambda x: pd.notna(x) and math.isfinite(x) and x > 0).all():
        raise ValueError('Use valid timestamps and positive finite amounts.')
    if data['transaction_id'].duplicated().any():
        raise ValueError('Transaction IDs must be unique.')
    if not data['direction'].isin(['Debit', 'Credit']).all():
        raise ValueError('Direction must be Debit or Credit.')
    data = data.sort_values(['timestamp', 'transaction_id']).reset_index(drop=True)
    if 'customer_id' not in data:
        data['customer_id'] = data['account_id']
    if data['customer_id'].isna().any() or data['customer_id'].astype(str).str.strip().eq('').any():
        raise ValueError('Customer IDs cannot be empty.')
    data['history_count'] = 0
    data['prior_mean'] = float('nan')
    # Baselines compare same-direction activity and exclude the current timestamp.
    for _, group in data.groupby(['customer_id', 'direction']):
        prior = []
        for _, simultaneous in group.groupby('timestamp', sort=True):
            data.loc[simultaneous.index, 'history_count'] = len(prior)
            if prior:
                data.loc[simultaneous.index, 'prior_mean'] = sum(prior) / len(prior)
            prior.extend(simultaneous['amount'].tolist())
    data['relative_ratio'] = data['amount'] / data['prior_mean']
    data['relative_amount'] = (data['history_count'] >= config.min_history) & (data['relative_ratio'] >= config.relative_multiplier)
    data['window_count'] = 0
    window = pd.Timedelta(minutes=config.window_minutes).value
    for _, group in data.groupby('customer_id'):
        times = group['timestamp'].astype('int64').to_numpy()
        counts = times.searchsorted(times, side='right') - times.searchsorted(times - window, side='left')
        data.loc[group.index, 'window_count'] = counts
    data['large_amount'] = data['amount'] >= config.large_amount
    data['high_frequency'] = data['window_count'] >= config.frequency_count
    data['amount_points'] = data['large_amount'].astype(int) * 35
    data['relative_points'] = data['relative_amount'].astype(int) * 25
    data['frequency_points'] = data['high_frequency'].astype(int) * 30
    data['combined_points'] = ((data['large_amount'].astype(int) + data['relative_amount'].astype(int) + data['high_frequency'].astype(int)) >= 2).astype(int) * 10
    data['risk_score'] = data['amount_points'] + data['relative_points'] + data['frequency_points'] + data['combined_points']
    data['flagged'] = data['risk_score'] >= config.flag_score
    data['risk_level'] = pd.cut(data['risk_score'], bins=[-1, 0, 39, 69, 100], labels=['Minimal', 'Low', 'Elevated', 'High']).astype(str)
    def explain(row):
        reasons = []
        if row['large_amount']:
            reasons.append('Amount ${:,.2f} ≥ ${:,.2f}: +35'.format(row['amount'], config.large_amount))
        if row['relative_amount']:
            reasons.append('Amount {:.2f}× prior same-direction mean ${:,.2f} ≥ {:.2f}×: +25'.format(row['relative_ratio'], row['prior_mean'], config.relative_multiplier))
        if row['history_count'] < config.min_history:
            reasons.append('Relative rule inactive: {} prior records; {} required'.format(row['history_count'], config.min_history))
        if row['high_frequency']:
            reasons.append('{} transactions in trailing {} minutes ≥ {}: +30'.format(row['window_count'], config.window_minutes, config.frequency_count))
        if row['combined_points']:
            reasons.append('Multiple rules met: +10')
        return '; '.join(reasons) or 'No rules triggered: 0 points'
    data['explanation'] = data.apply(explain, axis=1)
    return data


def financial_analyses(data):
    """Three views: cash flow, account concentration, and channel exposure."""
    if data.empty:
        return pd.DataFrame(columns=['Credit', 'Debit', 'Net flow']), pd.DataFrame(), pd.DataFrame()
    daily = data.assign(day=data['timestamp'].dt.floor('D')).pivot_table(
        index='day', columns='direction', values='amount', aggfunc='sum', fill_value=0)
    daily = daily.reindex(columns=['Credit', 'Debit'], fill_value=0)
    daily['Net flow'] = daily['Credit'] - daily['Debit']
    accounts = data.groupby('account_id').agg(total_value=('amount', 'sum'),
        average_amount=('amount', 'mean'), transactions=('amount', 'size'), flagged_transactions=('flagged', 'sum'))
    accounts['value_share_pct'] = 100 * accounts['total_value'] / accounts['total_value'].sum()
    accounts = accounts.sort_values('total_value', ascending=False)
    channels = data.assign(flagged_value=data['amount'].where(data['flagged'], 0)).groupby('channel').agg(
        total_value=('amount', 'sum'), transactions=('amount', 'size'),
        flagged_value=('flagged_value', 'sum'), flagged_transactions=('flagged', 'sum'))
    channels['flag_rate_pct'] = 100 * channels['flagged_transactions'] / channels['transactions']
    return daily, accounts, channels


def summary_metrics(data):
    """Gross volume, arithmetic average, and alert exposure with safe empty results."""
    count = len(data)
    total = float(data['amount'].sum()) if count else 0.0
    flagged = data[data['flagged']] if count else data
    return dict(count=count, total=total, average=total / count if count else 0.0,
                flagged_count=len(flagged), flagged_pct=100 * len(flagged) / count if count else 0.0,
                flagged_value=float(flagged['amount'].sum()) if len(flagged) else 0.0)
