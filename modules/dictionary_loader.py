def load_dictionary_values(cursor, dictionary_id):

    if not dictionary_id:
        return []

    cursor.execute("""
        SELECT value_text
        FROM report_dictionary_values
        WHERE dictionary_id = %s
        ORDER BY display_order, id
    """, (dictionary_id,))

    rows = cursor.fetchall()

    return [row[0] for row in rows]