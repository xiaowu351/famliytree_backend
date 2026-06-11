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


def render_reportlab_pdf(output_path, payload):
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
