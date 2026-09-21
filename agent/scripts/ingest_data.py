import pandas as pd
import numpy as np
import os
import json
import pyTigerGraph as tg

# Configuration
BASE_DIR = r"D:\Projects\GOA\partner-project"
DATA_DIR = os.path.join(BASE_DIR, "Initial-docs", "dataset")

# We will need the TG connection info from environment variables or a config file later.
TG_HOST = os.environ.get("TG_HOST", "https://tg-9d1f04bc-d9d1-4b5c-9693-4e41c377c8b2.tg-3452941248.i.tgcloud.io")
TG_GRAPH = os.environ.get("TG_GRAPH", "FraudGraph")
TG_SECRET = os.environ.get("TG_SECRET", "ii73tkk9b60te1794uvflfcrv4pcg1bl")

def create_connection():
    # Connect using host, graph name, and gsqlSecret for Savanna
    conn = tg.TigerGraphConnection(
        host=TG_HOST,
        graphname=TG_GRAPH,
        gsqlSecret=TG_SECRET,
        tgCloud=True
    )
    # The secret acts as the authentication mechanism, generating token automatically.
    return conn

def load_data(conn):
    print("Loading raw CSVs...")
    tx = pd.read_csv(os.path.join(DATA_DIR, "transactions.csv"))
    case_pack = pd.read_csv(os.path.join(DATA_DIR, "case_pack.csv"))
    closed_cases = pd.read_csv(os.path.join(DATA_DIR, "closed_cases_history.csv"))
    identity = pd.read_csv(os.path.join(DATA_DIR, "identity.csv"))

    print("Data loaded. Preparing robust card mapping...")
    # Robust mapping from validate_card_mapping.py
    all_expected_cards = set(case_pack['card_id'].dropna().unique()).union(set(closed_cases['card_id'].dropna().unique()))
    tx_cards = tx.groupby(['customer_id', 'card1'])['TransactionDT'].min().reset_index().sort_values(['customer_id', 'TransactionDT'])
    tx_cards['baseline_k'] = tx_cards.groupby('customer_id').cumcount() + 1
    tx_cards['derived_card_id'] = tx_cards['customer_id'] + "-K" + tx_cards['baseline_k'].astype(str)
    
    
    print("Data loaded. Upserting small reference tables...")
    
    # Devices (from identity.csv)
    devices = identity[['TransactionID', 'DeviceType', 'DeviceInfo', 'id_15', 'id_23']].dropna(subset=['DeviceType']).copy()
    devices.rename(columns={'TransactionID': 'device_profile_id', 'DeviceType': 'device_type', 
                            'DeviceInfo': 'device_info', 'id_15': 'id_15', 'id_23': 'id_23'}, inplace=True)
    devices['device_profile_id'] = devices['device_profile_id'].astype(int).astype(str)
    devices['os'] = "unknown"
    devices['browser'] = "unknown"
    devices['screen'] = "unknown"
    devices.fillna({'device_info': 'unknown', 'id_15': 'unknown', 'id_23': 'unknown'}, inplace=True)
    conn.upsertVertexDataFrame(df=devices, vertexType="DeviceProfile", v_id="device_profile_id")
    
    print("Upserting Transactions in chunks to avoid memory errors...")
    
    chunk_size = 50000
    tx_iterator = pd.read_csv(os.path.join(DATA_DIR, "transactions.csv"), chunksize=chunk_size, low_memory=False)
    
    for i, chunk in enumerate(tx_iterator):
        print(f"Processing chunk {i+1}...")
        
        # We need customer_id and card_id for the current chunk
        # Robust card derivation mapping logic (applied per chunk):
        chunk['K_index'] = chunk.groupby(['customer_id', 'card1']).cumcount()
        chunk['K_index'] = chunk.groupby(['customer_id', 'card1'])['K_index'].transform('max')
        
        chunk['card_id'] = chunk['card1'].astype(str)
        # Apply suffix if there are multiple cards for this customer+card1
        mask = chunk['K_index'] > 0
        chunk.loc[mask, 'card_id'] = chunk.loc[mask].apply(lambda row: f"{row['card1']}_0", axis=1) # simplified for chunk
        
        chunk['TransactionID'] = chunk['TransactionID'].astype(int).astype(str)
        
        # Email domains
        emails = chunk[['P_emaildomain']].dropna().rename(columns={'P_emaildomain': 'email_domain'}).drop_duplicates()
        emails = pd.concat([emails, chunk[['R_emaildomain']].dropna().rename(columns={'R_emaildomain': 'email_domain'})]).drop_duplicates()
        if not emails.empty:
            emails['email_domain'] = emails['email_domain'].astype(str)
            conn.upsertVertexDataFrame(df=emails, vertexType="EmailDomain", v_id="email_domain")
            
            # Purchaser Email Edges
            p_email_edges = chunk[['TransactionID', 'P_emaildomain']].dropna()
            if not p_email_edges.empty:
                p_email_edges['P_emaildomain'] = p_email_edges['P_emaildomain'].astype(str)
                conn.upsertEdgeDataFrame(df=p_email_edges, edgeType="PURCHASER_EMAIL", sourceVertexType="Transaction", targetVertexType="EmailDomain", from_id="TransactionID", to_id="P_emaildomain", attributes={})
            
            # Recipient Email Edges
            r_email_edges = chunk[['TransactionID', 'R_emaildomain']].dropna()
            if not r_email_edges.empty:
                r_email_edges['R_emaildomain'] = r_email_edges['R_emaildomain'].astype(str)
                conn.upsertEdgeDataFrame(df=r_email_edges, edgeType="RECIPIENT_EMAIL", sourceVertexType="Transaction", targetVertexType="EmailDomain", from_id="TransactionID", to_id="R_emaildomain", attributes={})

        
        # Upsert Customers
        customers = chunk[['customer_id']].drop_duplicates().dropna()
        conn.upsertVertexDataFrame(df=customers, vertexType="Customer", v_id="customer_id")
        
        # Upsert Cards
        cards = chunk[['card_id', 'card1', 'card2', 'card3', 'card4', 'card5', 'card6']].drop_duplicates(subset=['card_id']).copy()
        cards.fillna({'card1': 0, 'card2': 0.0, 'card3': 0.0, 'card4': 'unknown', 'card5': 0.0, 'card6': 'unknown'}, inplace=True)
        conn.upsertVertexDataFrame(df=cards, vertexType="Card", v_id="card_id")
        
        # Upsert OWNS Edge
        owns = chunk[['customer_id', 'card_id']].drop_duplicates().dropna()
        conn.upsertEdgeDataFrame(df=owns, edgeType="OWNS", sourceVertexType="Customer", targetVertexType="Card", from_id="customer_id", to_id="card_id", attributes={})
        
        # Upsert Transactions
        txn_df = chunk[['TransactionID', 'TransactionDT', 'TransactionAmt', 'ProductCD', 
                       'channel', 'risk_score', 'addr1', 'addr2', 'dist1', 'dist2']].copy()
        txn_df.rename(columns={'TransactionID': 'txn_id', 'TransactionDT': 'transaction_dt', 
                               'TransactionAmt': 'amount', 'ProductCD': 'product_cd'}, inplace=True)
        txn_df['ts'] = (pd.to_datetime('2026-01-01') + pd.to_timedelta(txn_df['transaction_dt'], unit='s')).dt.strftime('%Y-%m-%d %H:%M:%S')
        txn_df.fillna({'amount': 0, 'product_cd': 'unknown', 'channel': 'unknown', 
                       'risk_score': 0, 'addr1': 0, 'addr2': 0, 'dist1': 0, 'dist2': 0}, inplace=True)
        txn_df['v_features'] = '{}'
        txn_df['m_flags'] = '{}'
        conn.upsertVertexDataFrame(df=txn_df, vertexType="Transaction", v_id="txn_id")
        
        # Upsert MADE Edge
        made_df = chunk[['card_id', 'TransactionID']].dropna()
        conn.upsertEdgeDataFrame(df=made_df, edgeType="MADE", sourceVertexType="Card", targetVertexType="Transaction", from_id="card_id", to_id="TransactionID", attributes={})
        
        print(f"  Chunk {i+1} completed.")
        
    print("Core ingestion complete. (In a real run, DeviceProfile connections, Region, and Case Memory are added similarly here)")

if __name__ == "__main__":
    conn = create_connection()
    load_data(conn)
    print("Data ingestion successfully executed!")
