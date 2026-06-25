import html
import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr


DEFAULT_PREFACE = '凡国必有史，有家必有谱。族谱延续着家族的血脉，传承着祖上的遗训和期待。'


def group_members_by_generation(members):
    generation_map = {}
    for member in members:
        if member.is_spouse:
            continue
        generation = member.generation or 1
        generation_map.setdefault(generation, []).append(member)

    grouped = []
    for generation in sorted(generation_map):
        grouped.append({
            'generation': generation,
            'members': sorted(
                generation_map[generation],
                key=lambda item: (item.rank_type or '', item.create_time or '', item.name or '')
            )
        })
    return grouped


GENERATION_NAMES = ['始祖', '前一世', '元祖', '一世', '二世', '三世', '四世', '五世', '六世', '七世']


def _compact_name(name, fallback='未名', limit=6):
    return ''.join(str(name or fallback).split())[:limit]


def _generation_label(generation):
    try:
        number = int(generation or 1)
    except (TypeError, ValueError):
        number = 1
    if 1 <= number <= len(GENERATION_NAMES):
        return GENERATION_NAMES[number - 1]
    return f'{number}世'


def build_preview_pages_payload(tree, members):
    title = tree.title or (f'{tree.surname}氏宗谱' if tree.surname else '家族谱书')
    main_members = [member for member in members if not member.is_spouse]
    groups = [{
        'generation': group['generation'],
        'label': _generation_label(group['generation']),
        'members': group['members'],
    } for group in group_members_by_generation(members)]

    lineage_groups = [{
        'key': group['generation'],
        'label': group['label'],
        'names': [{'id': member.id, 'name': _compact_name(member.name)} for member in group['members'][:7]],
    } for group in groups]

    roots = groups[0]['members'] if groups else []
    if not roots:
        roots = [member for member in main_members if not member.parent_id]
    root = roots[0] if roots else (main_members[0] if main_members else None)

    children_map = {}
    for member in main_members:
        children_map.setdefault(member.parent_id or 'root', []).append(member)
    for key in list(children_map.keys()):
        children_map[key].sort(key=lambda item: (str(item.birth_order or ''), item.create_time or '', item.name or ''))

    branch_base = (children_map.get(root.id, []) if root else []) or (groups[1]['members'][:5] if len(groups) > 1 else [])
    main_line_members = ([root] if root else []) + branch_base[:2] + (groups[2]['members'][:1] if len(groups) > 2 else [])
    main_line = [{'id': member.id, 'name': _compact_name(member.name)} for member in main_line_members if member]
    branch_children = [{'id': member.id, 'name': _compact_name(member.name)} for member in branch_base[:5]]

    member_by_id = {member.id: member for member in members}
    spouses_by_member = {}
    for member in members:
        if member.is_spouse and member.spouse_id:
            spouses_by_member.setdefault(member.spouse_id, []).append(member)

    spread_groups = []
    for group in groups[:7]:
        spread_groups.append({
            'key': group['generation'],
            'label': group['label'],
            'members': [{
                'id': member.id,
                'name': _compact_name(member.name),
                'parent': _compact_name(member_by_id.get(member.parent_id).name, '', 6) if member.parent_id and member_by_id.get(member.parent_id) else '',
                'spouse': _compact_name(spouses_by_member.get(member.id, [None])[0].name, '', 6) if spouses_by_member.get(member.id) else '',
            } for member in group['members'][:8]]
        })

    line_members = [group['members'][0] for group in groups[1:6] if group['members']]
    if not line_members:
        line_members = [member for member in main_line_members if member]

    pages = [
        {'type': 'toc', 'catalogTitle': '全卷目录', 'title': title, 'sectionTitle': '全卷目录', 'sideText': '目录', 'lineageGroups': lineage_groups},
        {'type': 'blank', 'catalogTitle': '空白衬页', 'title': title, 'sideText': ''},
        {'type': 'index', 'catalogTitle': f'{title}检索表', 'title': title, 'sideText': f'{title}派下检索表', 'lineageGroups': lineage_groups},
        {'type': 'tree', 'catalogTitle': f'{title}世系图', 'title': title, 'sideText': f'{title}派下前一至三世', 'tabs': lineage_groups[:5], 'mainLine': main_line, 'branchChildren': branch_children},
        {'type': 'line', 'catalogTitle': f'{title}世系续图', 'title': title, 'sideText': f'{title}派下二至六世', 'tabs': lineage_groups[3:8], 'mainLine': [{'id': member.id, 'name': _compact_name(member.name)} for member in line_members if member]},
        {'type': 'spread', 'catalogTitle': f'{title}派下世表', 'title': title, 'sideText': f'{title}派下前一至三世', 'spreadGroups': spread_groups[:5]},
        {'type': 'spread', 'catalogTitle': f'{title}派下世表续', 'title': title, 'sideText': f'{title}派下三至七世', 'spreadGroups': spread_groups[2:7]},
        {'type': 'blank', 'catalogTitle': '空白衬页', 'title': title, 'sideText': ''},
    ]
    for index, page in enumerate(pages):
        page['pageNo'] = index + 1
        page['pageNoText'] = f'〇{index + 1}'
        page['sidePosition'] = 'left' if index + 1 in (1, 5, 7) else 'right'
    return pages


def build_book_payload(tree, members, preface='', style='ink'):
    style = 'royal' if style == 'royal' else 'ink'
    if style == 'royal':
        accent = '#B08A42'
        deep = '#8B1A1A'
        pale = '#FFF8E8'
        card = '#FFFCF4'
        border = '#DFC078'
        muted = '#7A4D12'
    else:
        accent = '#2F3437'
        deep = '#1F2326'
        pale = '#F3F1EA'
        card = '#FBFAF5'
        border = '#C9C4B8'
        muted = '#566061'
    groups = []
    for group in group_members_by_generation(members):
        groups.append({
            'generation': group['generation'],
            'members': [{
                'name': member.name or '',
                'rank': member.rank_type or '',
                'gender': '女' if member.gender == 'F' else '男',
                'alive': '健在' if member.is_alive else '已故',
                'birth': member.birth_date or '未详',
                'desc': member.desc or member.achievements or '生平事略待补。',
            } for member in group['members']]
        })

    return {
        'title': f'{tree.surname or ""}氏{tree.title or "族谱"}',
        'subtitle': tree.hall_name or tree.region or '百家有谱',
        'hall_name': tree.hall_name or '未填写',
        'region': tree.region or '未填写',
        'member_count': len([member for member in members if not member.is_spouse]),
        'preface': preface or tree.preface or DEFAULT_PREFACE,
        'groups': groups,
        'preview_pages': build_preview_pages_payload(tree, members),
        'style': style,
        'accent': accent,
        'deep': deep,
        'pale': pale,
        'card': card,
        'border': border,
        'muted': muted,
    }


def build_book_html(tree, members, preface='', style='ink'):
    payload = build_book_payload(tree, members, preface, style)
    generation_html = []
    for group in payload['groups']:
        records = []
        for member in group['members']:
            records.append(f'''
              <div class="member-record">
                <div class="member-name">{html.escape(member['name'])}<span class="member-meta"> {html.escape(member['rank'])} {member['gender']} {member['alive']}</span></div>
                <div class="member-line">生辰：{html.escape(member['birth'])}</div>
                <div class="member-desc">{html.escape(member['desc'])}</div>
              </div>
            ''')
        generation_html.append(f'''
          <section class="generation-section">
            <h2 class="generation-title">第{group['generation']}世</h2>
            {''.join(records)}
          </section>
        ''')

    return f'''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    @page {{
      size: A4 portrait;
      margin: 2cm;
      @bottom-center {{
        content: "第 " counter(page) " 页";
        font-family: "SimSun", serif;
        font-size: 10pt;
        color: #666;
      }}
    }}
    body {{
      font-family: "STSong", "SimSun", serif;
      color: #333;
      line-height: 1.8;
      background: #fff;
    }}
    .page-border {{
      border: 4px double {payload['accent']};
      padding: 24px;
      min-height: 960px;
      box-sizing: border-box;
    }}
    .cover-page {{
      text-align: center;
      page-break-after: always;
    }}
    .book-title {{
      margin-top: 140px;
      font-size: 36pt;
      font-weight: bold;
      color: {payload['deep']};
      letter-spacing: 8px;
    }}
    .book-subtitle {{
      margin-top: 36px;
      font-size: 15pt;
      color: {payload['accent']};
    }}
    .preface-page {{
      page-break-after: always;
    }}
    .preface-title,
    .generation-title {{
      font-size: 18pt;
      color: {payload['accent']};
      border-bottom: 2px solid {payload['accent']};
      padding-bottom: 8px;
      margin-top: 20px;
    }}
    .preface-text {{
      margin-top: 24px;
      font-size: 13pt;
      text-indent: 2em;
    }}
    .member-record {{
      margin-bottom: 18px;
      padding-bottom: 10px;
      border-bottom: 1px dashed #ccc;
    }}
    .member-name {{
      font-size: 14pt;
      font-weight: bold;
    }}
    .member-meta,
    .member-line {{
      font-size: 11pt;
      color: #666;
    }}
    .member-desc {{
      margin-top: 4px;
      font-size: 12pt;
    }}
  </style>
</head>
<body>
  <div class="page-border cover-page">
    <div class="book-title">{html.escape(payload['title'])}</div>
    <div class="book-subtitle">{html.escape(payload['subtitle'])}</div>
  </div>
  <div class="page-border preface-page">
    <h1 class="preface-title">谱序</h1>
    <div class="preface-text">{html.escape(payload['preface']).replace(chr(10), '<br>')}</div>
  </div>
  <div class="page-border">
    {''.join(generation_html)}
  </div>
</body>
</html>'''


def _wrap_text(text, width=28):
    text = str(text or '').replace('\r', '').strip()
    if not text:
        return ['']
    wrapped = []
    for raw_line in text.split('\n'):
        line = raw_line.strip()
        while len(line) > width:
            wrapped.append(line[:width])
            line = line[width:]
        wrapped.append(line)
    return wrapped


def _reportlab_font_name():
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        font_name = 'STSong-Light'
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(UnicodeCIDFont(font_name))
        return font_name
    except Exception:
        return 'Helvetica'


def _draw_frame(pdf, page_width, page_height, margin, accent, title='', page_no=None, font_name='STSong-Light'):
    pdf.setStrokeColor(accent)
    pdf.setLineWidth(1.2)
    pdf.rect(margin / 2, margin / 2, page_width - margin, page_height - margin)
    pdf.setLineWidth(0.45)
    pdf.rect(margin / 2 + 5, margin / 2 + 5, page_width - margin - 10, page_height - margin - 10)
    if title:
        pdf.setFont(font_name, 9)
        pdf.setFillColor(accent)
        pdf.drawString(margin, page_height - margin / 2 + 2, title)
    if page_no:
        pdf.setFont(font_name, 9)
        pdf.setFillColorRGB(0.45, 0.45, 0.45)
        pdf.drawCentredString(page_width / 2, margin / 2 - 5, f'第 {page_no} 页')
    pdf.setFillColorRGB(0, 0, 0)


def _draw_vertical_text(pdf, text, x, y, font_name, font_size=11, line_gap=1.05, max_chars=None):
    safe_text = str(text or '')
    if max_chars:
        safe_text = safe_text[:max_chars]
    pdf.setFont(font_name, font_size)
    cursor_y = y
    for char in safe_text:
        pdf.drawCentredString(x, cursor_y, char)
        cursor_y -= font_size * line_gap


def _draw_preview_shell(pdf, page, page_width, page_height, font_name):
    from reportlab.lib import colors
    pdf.setFillColor(colors.white)
    pdf.rect(0, 0, page_width, page_height, fill=1, stroke=0)
    pdf.saveState()
    pdf.setFillColor(colors.HexColor('#A07D5A'))
    try:
        pdf.setFillAlpha(0.12)
    except Exception:
        pass
    for row in range(4):
        for col in range(3):
            x = 78 + col * 170
            y = page_height - 90 - row * 185
            pdf.saveState()
            pdf.translate(x, y)
            pdf.rotate(-18)
            pdf.setStrokeColor(colors.HexColor('#A07D5A'))
            pdf.setLineWidth(1.2)
            pdf.circle(0, 0, 16, stroke=1, fill=0)
            pdf.setFont(font_name, 16)
            pdf.drawCentredString(0, -5, '谱')
            pdf.setFont(font_name, 15)
            pdf.drawString(24, 2, '百家有谱')
            pdf.setFont(font_name, 6)
            pdf.drawString(25, -11, 'BAIJIA YOUPU')
            pdf.restoreState()
    try:
        pdf.setFillAlpha(1)
    except Exception:
        pass
    pdf.restoreState()
    pdf.setStrokeColor(colors.black)
    pdf.setLineWidth(1.4)
    pdf.line(0, page_height - 8, page_width, page_height - 8)
    pdf.line(0, 8, page_width, 8)
    side_w = 38
    is_left_side = page.get('sidePosition') == 'left'
    pdf.setLineWidth(0.8)
    if is_left_side:
        pdf.line(side_w, 8, side_w, page_height - 8)
        title_x = 18
        ribbon_x = 0
        side_text_x = 30
        page_no_x = side_w + 8
    else:
        pdf.line(page_width - side_w, 8, page_width - side_w, page_height - 8)
        title_x = page_width - 18
        ribbon_x = page_width - side_w
        side_text_x = page_width - 30
        page_no_x = page_width - side_w - 8
    _draw_vertical_text(pdf, page.get('title'), title_x, page_height - 26, font_name, 15, max_chars=14)
    pdf.setFillColor(colors.black)
    pdf.saveState()
    pdf.skew(0, -14)
    pdf.rect(ribbon_x, page_height - 122, side_w, 16, fill=1, stroke=0)
    pdf.restoreState()
    if page.get('sideText'):
        _draw_vertical_text(pdf, page.get('sideText'), side_text_x, page_height - 145, font_name, 8, max_chars=18)
    pdf.setFillColor(colors.HexColor('#777777'))
    _draw_vertical_text(pdf, page.get('pageNoText'), page_no_x, 58, font_name, 8)
    pdf.setFillColor(colors.black)


def _draw_toc_page(pdf, page, page_width, page_height, font_name):
    _draw_preview_shell(pdf, page, page_width, page_height, font_name)
    _draw_vertical_text(pdf, page.get('sectionTitle'), page_width - 72, page_height - 60, font_name, 13, max_chars=8)
    x = page_width - 120
    for index, group in enumerate(page.get('lineageGroups') or []):
        _draw_vertical_text(pdf, group.get('label'), x, page_height - 50, font_name, 8, max_chars=8)
        pdf.setDash(1, 2)
        pdf.line(x, page_height - 118, x, page_height - 245)
        pdf.setDash()
        _draw_vertical_text(pdf, f'{index + 2}页', x, page_height - 260, font_name, 7)
        x -= 24
        if x < 45:
            break


def _draw_black_vertical_tab(pdf, label, x, y, width, height, font_name):
    from reportlab.lib import colors
    pdf.saveState()
    pdf.setFillColor(colors.black)
    pdf.roundRect(x, y, width, height, 4, stroke=0, fill=1)
    pdf.setStrokeColor(colors.HexColor('#777777'))
    pdf.roundRect(x + 1, y + 1, width - 2, height - 2, 3, stroke=1, fill=0)
    pdf.setFillColor(colors.white)
    _draw_vertical_text(pdf, label, x + width / 2, y + height - 10, font_name, 7, max_chars=6)
    pdf.restoreState()


def _draw_index_page(pdf, page, page_width, page_height, font_name):
    _draw_preview_shell(pdf, page, page_width, page_height, font_name)
    for x in (170, 300, 430):
        pdf.line(x, 34, x, page_height - 28)
    y = page_height - 42
    for index, group in enumerate(page.get('lineageGroups') or []):
        x = page_width - 105
        _draw_black_vertical_tab(pdf, group.get('label'), x - 12, y - 42, 26, 48, font_name)
        name_x = x - 28
        for person in group.get('names') or []:
            _draw_vertical_text(pdf, person.get('name'), name_x, y, font_name, 8, max_chars=6)
            name_x -= 16
        _draw_vertical_text(pdf, f'{index + 2}页', name_x - 8, y, font_name, 7)
        y -= 48
        if y < 50:
            break


def _draw_lineage_page(pdf, page, page_width, page_height, font_name):
    _draw_preview_shell(pdf, page, page_width, page_height, font_name)
    x = page_width / 2 - 26
    y = page_height - 70
    people = page.get('mainLine') or []
    for index, person in enumerate(people):
        _draw_vertical_text(pdf, person.get('name'), x, y, font_name, 12, max_chars=6)
        pdf.circle(x, y - 44, 4, stroke=1, fill=0)
        if index < len(people) - 1:
            pdf.line(x, y - 50, x, y - 96)
        y -= 92
    children = page.get('branchChildren') or []
    if children:
        base_y = max(70, y + 30)
        start_x = x - (len(children) - 1) * 20
        pdf.line(start_x - 12, base_y + 18, start_x + len(children) * 40 - 28, base_y + 18)
        for index, child in enumerate(children):
            cx = start_x + index * 40
            pdf.line(cx, base_y + 18, cx, base_y + 6)
            _draw_vertical_text(pdf, child.get('name'), cx, base_y, font_name, 9, max_chars=5)
    tx = page_width - 78
    for tab in page.get('tabs') or []:
        _draw_black_vertical_tab(pdf, tab.get('label'), tx - 11, page_height - 96, 22, 60, font_name)
        tx -= 28
        if tx < 60:
            break


def _draw_spread_page(pdf, page, page_width, page_height, font_name):
    _draw_preview_shell(pdf, page, page_width, page_height, font_name)
    row_h = (page_height - 40) / 5
    y_top = page_height - 24
    for index, group in enumerate(page.get('spreadGroups') or []):
        y = y_top - index * row_h
        if index:
            pdf.line(12, y, page_width - 40, y)
        x = page_width - 96
        for person in group.get('members') or []:
            text_parts = []
            if person.get('parent'):
                text_parts.append(f"生子{person.get('parent')}")
            text_parts.append(person.get('name') or '')
            if person.get('spouse'):
                text_parts.append(f"配{person.get('spouse')}")
            _draw_vertical_text(pdf, ''.join(text_parts), x, y - 18, font_name, 8, max_chars=13)
            x -= 26
            if x < 40:
                break
        _draw_black_vertical_tab(pdf, group.get('label'), page_width - 70, y - 72, 24, 58, font_name)


def render_preview_reportlab_pdf(output_path, payload):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    pages = payload.get('preview_pages') or []
    if not pages:
        return False
    font_name = _reportlab_font_name()
    page_width, page_height = A4
    pdf = canvas.Canvas(output_path, pagesize=A4)
    pdf.setTitle(payload.get('title') or '家族谱书')
    for page in pages:
        page_type = page.get('type')
        if page_type == 'toc':
            _draw_toc_page(pdf, page, page_width, page_height, font_name)
        elif page_type == 'index':
            _draw_index_page(pdf, page, page_width, page_height, font_name)
        elif page_type in ('tree', 'line'):
            _draw_lineage_page(pdf, page, page_width, page_height, font_name)
        elif page_type == 'spread':
            _draw_spread_page(pdf, page, page_width, page_height, font_name)
        else:
            _draw_preview_shell(pdf, page, page_width, page_height, font_name)
        pdf.showPage()
    pdf.save()
    return True


def render_reportlab_pdf(output_path, payload):
    if render_preview_reportlab_pdf(output_path, payload):
        return

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    font_name = _reportlab_font_name()
    page_width, page_height = A4
    pdf = canvas.Canvas(output_path, pagesize=A4)
    pdf.setTitle(payload.get('title') or '家族谱书')

    margin = 24 * mm
    accent = colors.HexColor(payload.get('accent') or '#A07D5A')
    deep = colors.HexColor(payload.get('deep') or '#8B1A1A')
    muted = colors.HexColor(payload.get('muted') or '#6F5349')
    pale = colors.HexColor(payload.get('pale') or '#F7F2EC')
    card_color = colors.HexColor(payload.get('card') or '#FFFCF8')
    card_border = colors.HexColor(payload.get('border') or '#E8D5B5')
    ink = colors.HexColor('#2F2925')
    title = payload.get('title') or '家族谱书'
    page_no = 1

    # Cover
    _draw_frame(pdf, page_width, page_height, margin, accent, font_name=font_name)
    pdf.setFillColor(pale)
    pdf.roundRect(margin, page_height - margin - 62 * mm, page_width - margin * 2, 48 * mm, 6, fill=1, stroke=0)
    pdf.setFillColor(deep)
    pdf.circle(page_width / 2, page_height - margin - 38 * mm, 18 * mm, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont(font_name, 24)
    pdf.drawCentredString(page_width / 2, page_height - margin - 42 * mm, title[:1] or '谱')
    pdf.setFillColor(deep)
    pdf.setFont(font_name, 30)
    pdf.drawCentredString(page_width / 2, page_height - margin - 88 * mm, title)
    pdf.setFillColor(accent)
    pdf.setFont(font_name, 15)
    pdf.drawCentredString(page_width / 2, page_height - margin - 106 * mm, payload.get('subtitle') or '百家有谱')
    pdf.setFillColor(muted)
    pdf.setFont(font_name, 11)
    pdf.drawCentredString(page_width / 2, margin + 38 * mm, f"堂号：{payload.get('hall_name')}    地区：{payload.get('region')}")
    pdf.drawCentredString(page_width / 2, margin + 28 * mm, f"族员数：{payload.get('member_count')}")
    pdf.showPage()

    # Preface
    _draw_frame(pdf, page_width, page_height, margin, accent, title=title, page_no=page_no, font_name=font_name)
    page_no += 1
    pdf.setFillColor(deep)
    pdf.setFont(font_name, 22)
    pdf.drawCentredString(page_width / 2, page_height - margin - 10 * mm, '谱 序')
    pdf.setStrokeColor(accent)
    pdf.line(margin, page_height - margin - 18 * mm, page_width - margin, page_height - margin - 18 * mm)
    y = page_height - margin - 34 * mm
    pdf.setFillColor(ink)
    pdf.setFont(font_name, 13)
    for line in _wrap_text(payload.get('preface') or DEFAULT_PREFACE, width=30):
        pdf.drawString(margin + 8 * mm, y, line)
        y -= 9 * mm
        if y < margin + 20 * mm:
            pdf.showPage()
            _draw_frame(pdf, page_width, page_height, margin, accent, title=title, page_no=page_no, font_name=font_name)
            page_no += 1
            y = page_height - margin - 18 * mm
            pdf.setFont(font_name, 13)
            pdf.setFillColor(ink)
    pdf.showPage()

    # Register
    _draw_frame(pdf, page_width, page_height, margin, accent, title=title, page_no=page_no, font_name=font_name)
    page_no += 1
    y = page_height - margin - 12 * mm
    pdf.setFillColor(deep)
    pdf.setFont(font_name, 20)
    pdf.drawCentredString(page_width / 2, y, '齿 录')
    y -= 16 * mm

    for group in payload.get('groups') or []:
        if y < margin + 38 * mm:
            pdf.showPage()
            _draw_frame(pdf, page_width, page_height, margin, accent, title=title, page_no=page_no, font_name=font_name)
            page_no += 1
            y = page_height - margin - 18 * mm

        pdf.setFillColor(accent)
        pdf.setFont(font_name, 15)
        pdf.drawString(margin, y, f'第{group.get("generation")}世')
        pdf.setStrokeColor(accent)
        pdf.line(margin + 26 * mm, y - 2, page_width - margin, y - 2)
        y -= 11 * mm

        for member in group.get('members') or []:
            if y < margin + 38 * mm:
                pdf.showPage()
                _draw_frame(pdf, page_width, page_height, margin, accent, title=title, page_no=page_no, font_name=font_name)
                page_no += 1
                y = page_height - margin - 18 * mm

            card_h = 29 * mm
            pdf.setFillColor(card_color)
            pdf.roundRect(margin, y - card_h + 4, page_width - margin * 2, card_h, 4, fill=1, stroke=0)
            pdf.setStrokeColor(card_border)
            pdf.roundRect(margin, y - card_h + 4, page_width - margin * 2, card_h, 4, fill=0, stroke=1)
            pdf.setFillColor(deep)
            pdf.setFont(font_name, 14)
            pdf.drawString(margin + 6 * mm, y - 6 * mm, member.get('name') or '')
            pdf.setFillColor(muted)
            pdf.setFont(font_name, 10)
            meta = f"{member.get('rank') or ''}  {member.get('gender') or ''}  {member.get('alive') or ''}  生辰：{member.get('birth') or '未详'}"
            pdf.drawString(margin + 6 * mm, y - 13 * mm, meta)
            pdf.setFillColor(ink)
            pdf.setFont(font_name, 10)
            desc = _wrap_text(member.get('desc') or '生平事略待补。', width=38)[0]
            pdf.drawString(margin + 6 * mm, y - 21 * mm, f'生平：{desc}')
            y -= card_h + 5 * mm

    pdf.save()


def _pdf_hex_text(text):
    return text.encode('utf-16-be').hex().upper()


def _simple_pdf_bytes(lines):
    page_lines = []
    for line in lines:
        page_lines.extend(_wrap_text(line))
    if not page_lines:
        page_lines = ['谱书内容为空']

    lines_per_page = 34
    pages = [page_lines[index:index + lines_per_page] for index in range(0, len(page_lines), lines_per_page)]
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        None,
        b'<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light /Encoding /UniGB-UCS2-H /DescendantFonts [4 0 R] >>',
        b'<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light /CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 2 >> /FontDescriptor 5 0 R >>',
        b'<< /Type /FontDescriptor /FontName /STSong-Light /Flags 6 /FontBBox [0 -200 1000 900] /ItalicAngle 0 /Ascent 880 /Descent -120 /CapHeight 700 /StemV 80 >>',
    ]
    page_object_numbers = []
    for page in pages:
        content_ops = ['BT', '/F1 13 Tf', '50 790 Td', '18 TL']
        for index, line in enumerate(page):
            if index:
                content_ops.append('T*')
            content_ops.append(f'<{_pdf_hex_text(line)}> Tj')
        content_ops.append('ET')
        stream = '\n'.join(content_ops).encode('ascii')
        page_obj_num = len(objects) + 1
        content_obj_num = page_obj_num + 1
        page_object_numbers.append(page_obj_num)
        objects.append(
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj_num} 0 R >>'.encode('ascii')
        )
        objects.append(b'<< /Length ' + str(len(stream)).encode('ascii') + b' >>\nstream\n' + stream + b'\nendstream')

    kids = ' '.join(f'{num} 0 R' for num in page_object_numbers)
    objects[1] = f'<< /Type /Pages /Kids [{kids}] /Count {len(page_object_numbers)} >>'.encode('ascii')
    body = [b'%PDF-1.4\n%\xE2\xE3\xCF\xD3\n']
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in body))
        body.append(f'{idx} 0 obj\n'.encode('ascii') + obj + b'\nendobj\n')
    xref_offset = sum(len(part) for part in body)
    xref = [b'xref\n', f'0 {len(objects) + 1}\n'.encode('ascii'), b'0000000000 65535 f \n']
    for offset in offsets[1:]:
        xref.append(f'{offset:010d} 00000 n \n'.encode('ascii'))
    trailer = f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n'.encode('ascii')
    return b''.join(body + xref + [trailer])


def render_pdf(html_content, output_path, fallback_payload):
    try:
        import reportlab  # noqa: F401
        render_reportlab_pdf(output_path, fallback_payload)
        if os.path.getsize(output_path) > 0:
            return 'reportlab'
    except Exception:
        pass

    try:
        from xhtml2pdf import pisa
        with open(output_path, 'wb') as output:
            result = pisa.CreatePDF(html_content, dest=output, encoding='utf-8')
        if not result.err and os.path.getsize(output_path) > 0:
            return 'xhtml2pdf'
    except Exception:
        pass

    lines = []
    if isinstance(fallback_payload, dict):
        lines = [
            fallback_payload.get('title') or '家族谱书',
            f"堂号：{fallback_payload.get('hall_name') or '未填写'}",
            f"地区：{fallback_payload.get('region') or '未填写'}",
            f"族员数：{fallback_payload.get('member_count') or 0}",
            '',
            '谱序',
            fallback_payload.get('preface') or DEFAULT_PREFACE,
            '',
            '齿录'
        ]
        for group in fallback_payload.get('groups') or []:
            lines.append(f"第{group.get('generation')}世")
            for member in group.get('members') or []:
                lines.append(f"{member.get('name')} {member.get('rank') or ''} {member.get('gender')} {member.get('alive')} 生辰：{member.get('birth')}")
    else:
        lines = fallback_payload

    with open(output_path, 'wb') as output:
        output.write(_simple_pdf_bytes(lines))
    return 'fallback'


def send_book_email(to_email, subject, body, attachment_path, filename):
    host = os.environ.get('SMTP_HOST', '')
    port = int(os.environ.get('SMTP_PORT', '465'))
    user = os.environ.get('SMTP_USER', '')
    password = os.environ.get('SMTP_PASSWORD', '')
    sender = os.environ.get('SMTP_FROM', user)
    sender_name = os.environ.get('SMTP_FROM_NAME', '百家有谱')
    if not host or not user or not password or not sender:
        return False, 'SMTP is not configured.'

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = formataddr((sender_name, sender))
    message['To'] = to_email
    message.set_content(body)
    with open(attachment_path, 'rb') as file_obj:
        message.add_attachment(file_obj.read(), maintype='application', subtype='pdf', filename=filename)

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
            smtp.login(user, password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(message)
    return True, 'sent'
