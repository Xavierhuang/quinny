def parse_csv_row(row):
    if not isinstance(row, str):
        raise TypeError("row must be a string")
    fields = []
    buf = []
    i = 0
    n = len(row)
    while i < n:
        ch = row[i]
        if ch == '"':
            # Quoted field must start at the beginning of a field.
            if buf:
                raise ValueError(f"unexpected quote at pos {i}")
            i += 1
            while True:
                if i >= n:
                    raise ValueError("unclosed quote")
                c = row[i]
                if c == '"':
                    # Doubled quote → literal ", or end of field.
                    if i + 1 < n and row[i + 1] == '"':
                        buf.append('"')
                        i += 2
                        continue
                    i += 1
                    # After closing quote we expect a comma or end of row.
                    if i < n and row[i] != ',':
                        raise ValueError(f"junk after closing quote at pos {i}")
                    break
                buf.append(c)
                i += 1
        elif ch == ',':
            fields.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(ch)
            i += 1
    fields.append("".join(buf))
    return fields
