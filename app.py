"""Project 9 — Financial Fraud and Transaction Monitoring."""
import streamlit as st
from monitoring import Thresholds, financial_analyses, generate_transactions, score_transactions

st.set_page_config(page_title='Project 9 | Fraud Monitor', page_icon='🏦', layout='wide')
st.title('🏦 Financial Fraud & Transaction Monitoring')
st.caption('Project 9 • Synthetic bank activity • Explainable rule-based screening')
st.info('All records are fictional. Risk scores prioritize review; they are not fraud probabilities or proof of fraud. Amounts are USD.')
with st.sidebar:
    st.header('Data & monitoring controls')
    count = st.number_input('Synthetic transactions', min_value=250, max_value=10000, value=500, step=250)
    seed = st.number_input('Random seed', min_value=0, max_value=1000000, value=9)
    large = st.number_input('Large amount threshold ($)', min_value=1.0, value=5000.0, step=500.0)
    frequency = st.slider('Transactions per account to trigger frequency rule', 2, 30, 5)
    window = st.slider('Trailing window (minutes)', 1, 1440, 60)
    cutoff = st.slider('Flag at risk score', 1, 100, 40)
    st.caption('Controls immediately recalculate the entire dataset. A fixed seed keeps the underlying transactions unchanged.')
try:
    data = score_transactions(generate_transactions(int(count), int(seed)), Thresholds(large, frequency, window, cutoff))
    daily, accounts, channels = financial_analyses(data)
except (ValueError, TypeError, OverflowError) as exc:
    st.error('Unable to analyze transactions: {}'.format(exc))
    st.stop()

flagged = data[data['flagged']]
cols = st.columns(4)
cols[0].metric('Transactions', '{:,}'.format(len(data)))
cols[1].metric('Total transaction value', '${:,.0f}'.format(data['amount'].sum()))
cols[2].metric('Flagged transactions', '{} ({:.1%})'.format(len(flagged), len(flagged) / len(data)))
cols[3].metric('Flagged value', '${:,.0f}'.format(flagged['amount'].sum()))
with st.expander('How risk scores work', expanded=False):
    st.markdown('**Large amount: 40 points. Frequent activity: 40 points. Both rules: 20 extra points.** Maximum score: 100. Threshold comparisons include equality. Frequency counts all account activity, including the current transaction and all simultaneous transactions, in the inclusive trailing window. Only transactions at or above the selected score are flagged.')
    st.caption('These fixed point weights are illustrative and have not been calibrated against real fraud outcomes. No balance, profitability, or loss is inferred from transaction volume.')

st.subheader('1. Cash flow over time')
st.write('Credits are inflows; debits are outflows. Net flow is credits minus debits, not an account balance.')
st.line_chart(daily[['Credit', 'Debit', 'Net flow']])
st.metric('Net flow for the period', '${:,.2f}'.format(daily['Net flow'].sum()))

left, right = st.columns(2)
with left:
    st.subheader('2. Account concentration')
    top_share = accounts.head(5)['value_share_pct'].sum()
    st.write('Top five accounts represent **{:.1f}%** of total transaction value (credits plus debits).'.format(top_share))
    st.bar_chart(accounts.head(10)['total_value'])
    st.dataframe(accounts, width='stretch')
with right:
    st.subheader('3. Channel risk exposure')
    st.write('Compare flagged value and review rates across payment channels. Flagged value represents activity requiring review, not confirmed losses.')
    st.bar_chart(channels[['total_value', 'flagged_value']])
    st.dataframe(channels.round(2), width='stretch')

st.subheader('Transaction review')
st.caption('Filters below affect the review table and its CSV export only; analyses and scores above use all generated records.')
a, b = st.columns(2)
selected = a.multiselect('Accounts', sorted(data['account_id'].unique()))
flagged_only = b.checkbox('Show flagged transactions only', value=True)
review = data[data['account_id'].isin(selected)] if selected else data
if flagged_only:
    review = review[review['flagged']]
review = review.sort_values(['risk_score', 'timestamp'], ascending=[False, False])
if review.empty:
    st.success('No transactions match the current review filters.')
else:
    st.dataframe(review, width='stretch', hide_index=True)
st.download_button('Download review CSV', review.to_csv(index=False).encode('utf-8'), 'transaction_review.csv', 'text/csv')
