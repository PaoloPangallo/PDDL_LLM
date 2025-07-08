import sqlite3
import msgpack
from pprint import pprint

def unpack_blob(blob):
    try:
        return msgpack.unpackb(blob, raw=False)
    except Exception as e:
        return f"<<Errore nel decodificare BLOB: {e}>>"

def list_checkpoints(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT thread_id FROM checkpoints")
    sessions = [row[0] for row in cursor.fetchall()]
    print("📚 Sessioni disponibili:")
    for i, session in enumerate(sessions, 1):
        print(f"  {i}. {session}")

    sel = input("\n👉 Seleziona sessione (numero): ")
    thread = sessions[int(sel) - 1]

    cursor.execute("SELECT checkpoint_id FROM checkpoints WHERE thread_id = ?", (thread,))
    checkpoints = [row[0] for row in cursor.fetchall()]
    print(f"\n⏳ Checkpoint nella sessione '{thread}':")
    for i, cp in enumerate(checkpoints, 1):
        print(f"  {i}. {cp}")

    sel_cp = input("\n👉 Seleziona checkpoint da esplorare (numero): ")
    return checkpoints[int(sel_cp) - 1]

def explore_checkpoint(db_path):
    conn = sqlite3.connect(db_path)
    checkpoint_id = list_checkpoints(conn)

    print(f"\n🔍 Estrazione da checkpoint: {checkpoint_id}")
    query = """
        SELECT channel, type, value
        FROM writes
        WHERE checkpoint_id = ?
        ORDER BY idx ASC
    """
    cursor = conn.cursor()
    cursor.execute(query, (checkpoint_id,))
    rows = cursor.fetchall()

    if not rows:
        print("⚠️ Nessun dato trovato per il checkpoint.")
    else:
        for channel, type_, blob in rows:
            print(f"\n📦 [channel: {channel}] - type: {type_}")
            value = unpack_blob(blob)
            pprint(value)

    conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Esplora uno snapshot LangGraph SQLite.")
    parser.add_argument("--db", type=str, required=True, help="Percorso al file .sqlite")
    args = parser.parse_args()

    explore_checkpoint(args.db)
