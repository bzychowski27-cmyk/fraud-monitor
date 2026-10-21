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
    flag_score: int = 40

    def validate(self):
        if not math.isfinite(self.large_amount) or self.large_amount <= 0:
            raise ValueError('Large-amount threshold must be positive and finite.')
        if self.frequency_count < 2 or self.window_minutes < 1:
            raise ValueError('Frequency count must be at least 2 and window at least 1 minute.')
        if not 1 <= self.flag_score <= 100:
            raise ValueError('Flag score must be between 1 and 100.')


def generate_transactions(count=500, seed=9):
    """Create reproducible fictional records, including large amounts and bursts."""
    if not isinstance(count, int) or count < 250:
        raise ValueError('Generate at least 250 transactions.')
    rng = random.Random(seed)
    start = datetime(2025, 1, 1)
    rows = []
    for i in range(count):
        rows.append({
            'transaction_id': 'TX{:05d}'.format(i + 1),
            'timestamp': start + timedelta(minutes=rng.randrange(30 * 24 * 60)),
            'account_id': 'AC{:03d}'.format(rng.randrange(1, 31)),
            'amount': round(min(rng.lognormvariate(5.6, 1.0), 4500), 2),
            'direction': rng.choice(['Debit', 'Credit']),
            'channel': rng.choice(['Card', 'Transfer', 'ATM', 'Online']),
            'category': rng.choice(['Retail', 'Bills', 'Travel', 'Income', 'Other']),
        })
    for i in range(8):
        rows[i]['amount'] = round(rng.uniform(8000, 25000), 2)
    for i in range(8, 20):
        rows[i].update(account_id='AC001', timestamp=start + timedelta(days=15, minutes=i - 8),
                       amount=round(rng.uniform(600, 1500), 2), direction='Debit', channel='Transfer')
    return pd.DataFrame(rows).sort_values(['timestamp', 'transaction_id']).reset_index(drop=True)


def score_transactions(frame, thresholds=None):
    """Score all records using a trailing per-account window inclusive of current record.

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
    if data[list(required)].isna().any().any():
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
    data['window_count'] = 0
    window = pd.Timedelta(minutes=config.window_minutes).value
    for _, group in data.groupby('account_id'):
        times = group['timestamp'].astype('int64').to_numpy()
        counts = times.searchsorted(times, side='right') - times.searchsorted(times - window, side='left')
        data.loc[group.index, 'window_count'] = counts
    data['large_amount'] = data['amount'] >= config.large_amount
    data['high_frequency'] = data['window_count'] >= config.frequency_count
    data['amount_points'] = data['large_amount'].astype(int) * 40
    data['frequency_points'] = data['high_frequency'].astype(int) * 40
    data['combined_points'] = (data['large_amount'] & data['high_frequency']).astype(int) * 20
    data['risk_score'] = data['amount_points'] + data['frequency_points'] + data['combined_points']
    data['flagged'] = data['risk_score'] >= config.flag_score
    def explain(row):
        reasons = []
        if row['large_amount']:
            reasons.append('Amount ${:,.2f} ≥ ${:,.2f}: +40'.format(row['amount'], config.large_amount))
        if row['high_frequency']:
            reasons.append('{} transactions in trailing {} minutes ≥ {}: +40'.format(row['window_count'], config.window_minutes, config.frequency_count))
        if row['combined_points']:
            reasons.append('Both rules met: +20')
        return '; '.join(reasons) or 'Neither rule met: 0 points'
    data['explanation'] = data.apply(explain, axis=1)
    return data


def financial_analyses(data):
    """Three views: cash flow, account concentration, and channel exposure."""
    daily = data.assign(day=data['timestamp'].dt.floor('D')).pivot_table(
        index='day', columns='direction', values='amount', aggfunc='sum', fill_value=0)
    daily = daily.reindex(columns=['Credit', 'Debit'], fill_value=0)
    daily['Net flow'] = daily['Credit'] - daily['Debit']
    accounts = data.groupby('account_id').agg(total_value=('amount', 'sum'),
        transactions=('amount', 'size'), flagged_transactions=('flagged', 'sum'))
    accounts['value_share_pct'] = 100 * accounts['total_value'] / accounts['total_value'].sum()
    accounts = accounts.sort_values('total_value', ascending=False)
    channels = data.assign(flagged_value=data['amount'].where(data['flagged'], 0)).groupby('channel').agg(
        total_value=('amount', 'sum'), transactions=('amount', 'size'),
        flagged_value=('flagged_value', 'sum'), flagged_transactions=('flagged', 'sum'))
    channels['flag_rate_pct'] = 100 * channels['flagged_transactions'] / channels['transactions']
    return daily, accounts, channels
