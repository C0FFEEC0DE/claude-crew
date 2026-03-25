"""Text rendering fixture used by benchmark tasks."""


def render_title(title):
    return title.strip().upper()


def render_subtitle(subtitle):
    return subtitle.strip().upper()


def render_metric(label, value):
    clean_label = label.strip().upper()
    clean_value = str(value).strip()
    return f"{clean_label}: {clean_value}"


def render_warning(label, value):
    clean_label = label.strip().upper()
    clean_value = str(value).strip()
    return f"WARNING {clean_label}: {clean_value}"

