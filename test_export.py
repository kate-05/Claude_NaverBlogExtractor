"""TC-08: Export functionality tests (JSON and CSV)."""
import sys, os, tempfile, json, csv
sys.path.insert(0, '.')

from pathlib import Path
from database.manager import DatabaseManager
from utils.helpers import export_to_json, export_to_csv
from config import Status

passed = failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f'  [PASS] {name}')
    else:
        failed += 1
        print(f'  [FAIL] {name}')

print('=' * 60)
print('TC-08: EXPORT FUNCTIONALITY TESTS')
print('=' * 60)

# Setup: create DB with test data
db_path = Path(tempfile.mktemp(suffix='.db'))
db = DatabaseManager(db_path)

# Populate data
db.add_blog('testblog', 'Test Blog Name', 'https://blog.naver.com/testblog',
            'Author Kim', 3)
db.update_blog_status('testblog', Status.COMPLETED)

db.add_post('testblog_001', 'testblog', 'First Post Title',
            'https://blog.naver.com/testblog/001')
db.update_post_content('testblog_001', title='First Post Title',
                       content='This is the first post content.\nWith multiple lines.',
                       category='Tech', post_date='2026-01-20')
db.update_post_crawl_status('testblog_001', Status.COMPLETED)

db.add_post('testblog_002', 'testblog', 'Second Post Title',
            'https://blog.naver.com/testblog/002')
db.update_post_content('testblog_002', title='Second Post Title',
                       content='Second post body text.',
                       category='Daily', post_date='2026-01-21')
db.update_post_crawl_status('testblog_002', Status.COMPLETED)

db.add_post('testblog_003', 'testblog', 'Third Post',
            'https://blog.naver.com/testblog/003')
db.update_post_content('testblog_003', title='Third Post',
                       content='Third post.',
                       category='Tech', post_date='2026-01-22')

# Reactions
db.add_reaction('testblog_001', 'like', 42)
db.add_reaction('testblog_001', 'fun', 10)
db.add_reaction('testblog_002', 'sympathy', 5)

# Comments with replies
db.add_comment('c1', 'testblog_001', 'Alice', 'Great post!', 5, '2026-01-20', is_reply=0)
db.add_comment('c2', 'testblog_001', 'Bob', 'Thanks Alice!', 2, '2026-01-20',
               parent_id='c1', is_reply=1)
db.add_comment('c3', 'testblog_001', 'Charlie', 'Nice content.', 3, '2026-01-21', is_reply=0)
db.add_comment('c4', 'testblog_002', 'Dave', 'Interesting.', 0, '2026-01-21', is_reply=0)

# --- TC-08-1: export_to_json basic ---
print('\n--- TC-08-1: JSON export basic ---')
tmp_json = tempfile.mktemp(suffix='.json')
data = {'test': 'value', 'number': 42, 'korean': '한글 테스트'}
result = export_to_json(data, tmp_json)
check('export_to_json returns True', result == True)
check('JSON file created', os.path.exists(tmp_json))

with open(tmp_json, 'r', encoding='utf-8') as f:
    loaded = json.load(f)
check('JSON content matches', loaded['test'] == 'value')
check('Korean preserved', loaded['korean'] == '한글 테스트')
check('Number preserved', loaded['number'] == 42)
os.unlink(tmp_json)

# --- TC-08-2: export_to_csv basic ---
print('\n--- TC-08-2: CSV export basic ---')
tmp_csv = tempfile.mktemp(suffix='.csv')
csv_data = [
    {'name': 'Alice', 'age': 30, 'city': 'Seoul'},
    {'name': 'Bob', 'age': 25, 'city': 'Busan'},
]
result = export_to_csv(csv_data, tmp_csv)
check('export_to_csv returns True', result == True)
check('CSV file created', os.path.exists(tmp_csv))

with open(tmp_csv, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
check('CSV has 2 rows', len(rows) == 2)
check('CSV first row name', rows[0]['name'] == 'Alice')
check('CSV second row city', rows[1]['city'] == 'Busan')
os.unlink(tmp_csv)

# --- TC-08-3: CSV with BOM (UTF-8-sig) ---
print('\n--- TC-08-3: CSV UTF-8-sig BOM ---')
tmp_csv = tempfile.mktemp(suffix='.csv')
csv_korean = [
    {'이름': '김철수', '나이': '30', '도시': '서울'},
    {'이름': '박영희', '나이': '25', '도시': '부산'},
]
export_to_csv(csv_korean, tmp_csv)
with open(tmp_csv, 'rb') as f:
    raw = f.read(3)
check('CSV has UTF-8 BOM', raw == b'\xef\xbb\xbf')

with open(tmp_csv, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
check('Korean headers parsed', '이름' in rows[0])
check('Korean values preserved', rows[0]['이름'] == '김철수')
os.unlink(tmp_csv)

# --- TC-08-4: CSV with custom fieldnames ---
print('\n--- TC-08-4: CSV custom fieldnames ---')
tmp_csv = tempfile.mktemp(suffix='.csv')
data = [
    {'a': 1, 'b': 2, 'c': 3, 'extra': 'ignored'},
    {'a': 4, 'b': 5, 'c': 6, 'extra': 'also ignored'},
]
result = export_to_csv(data, tmp_csv, fieldnames=['a', 'b', 'c'])
check('CSV with custom fieldnames', result == True)
with open(tmp_csv, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
check('Only specified columns', set(rows[0].keys()) == {'a', 'b', 'c'})
os.unlink(tmp_csv)

# --- TC-08-5: CSV empty data ---
print('\n--- TC-08-5: CSV edge cases ---')
tmp_csv = tempfile.mktemp(suffix='.csv')
result = export_to_csv([], tmp_csv)
check('Empty list returns False', result == False)

# --- TC-08-6: Full blog JSON export (simulating _export_data logic) ---
print('\n--- TC-08-6: Full blog JSON export ---')
tmp_json = tempfile.mktemp(suffix='.json')

blog = db.get_blog('testblog')
posts = db.get_blog_posts('testblog')

export_data = {
    'blog': {
        'id': blog['id'],
        'blog_name': blog['blog_name'],
        'author_name': blog.get('author_name', ''),
        'url': blog['url'],
    },
    'posts': []
}

for post in posts:
    post_data = dict(post)
    post_data['reactions'] = db.get_reactions(post['id'])
    comments = db.get_comments(post['id'])

    # Structure comments with replies nested
    top_comments = []
    reply_map = {}
    for c in comments:
        c_dict = dict(c)
        if c['is_reply'] and c.get('parent_id'):
            reply_map.setdefault(c['parent_id'], []).append(c_dict)
        else:
            c_dict['replies'] = []
            top_comments.append(c_dict)

    for tc in top_comments:
        tc['replies'] = reply_map.get(tc['id'], [])

    post_data['comments'] = top_comments
    export_data['posts'].append(post_data)

result = export_to_json(export_data, tmp_json)
check('Full JSON export succeeds', result == True)

with open(tmp_json, 'r', encoding='utf-8') as f:
    loaded = json.load(f)

check('Blog name in export', loaded['blog']['blog_name'] == 'Test Blog Name')
check('Author in export', loaded['blog']['author_name'] == 'Author Kim')
check('3 posts exported', len(loaded['posts']) == 3)

# Check first post details
p1 = loaded['posts'][0]
check('Post title present', p1['title'] == 'First Post Title')
check('Post content present', 'first post content' in p1.get('content', ''))
check('Post category present', p1.get('category') == 'Tech')

# Check reactions
r1 = p1.get('reactions', [])
check('Post has 2 reaction types', len(r1) == 2)
like_r = [r for r in r1 if r['reaction_type'] == 'like']
check('Like reaction count 42', len(like_r) == 1 and like_r[0]['count'] == 42)

# Check nested comments
c1 = p1.get('comments', [])
check('Post has 2 top-level comments', len(c1) == 2)
check('First comment author Alice', c1[0]['author'] == 'Alice')
check('First comment has replies', len(c1[0].get('replies', [])) == 1)
check('Reply is from Bob', c1[0]['replies'][0]['author'] == 'Bob')
check('Reply like_count is 2', c1[0]['replies'][0]['like_count'] == 2)
check('Second comment no replies', len(c1[1].get('replies', [])) == 0)

os.unlink(tmp_json)

# --- TC-08-7: Full blog CSV export (simulating _export_data logic) ---
print('\n--- TC-08-7: Full blog CSV export ---')
tmp_csv_posts = tempfile.mktemp(suffix='_posts.csv')
tmp_csv_comments = tempfile.mktemp(suffix='_comments.csv')

# Posts CSV
posts_csv = []
for p in posts:
    p_dict = dict(p)
    p_dict['blog_name'] = blog['blog_name']
    p_dict['author_name'] = blog.get('author_name', '')
    posts_csv.append(p_dict)

result = export_to_csv(posts_csv, tmp_csv_posts)
check('Posts CSV export succeeds', result == True)

with open(tmp_csv_posts, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
check('Posts CSV has 3 rows', len(rows) == 3)
check('Posts CSV has blog_name', rows[0].get('blog_name') == 'Test Blog Name')
check('Posts CSV has title', 'title' in rows[0])
check('Posts CSV has content', 'content' in rows[0])
os.unlink(tmp_csv_posts)

# Comments CSV
all_comments = []
for post in posts:
    comments = db.get_comments(post['id'])
    for c in comments:
        c_dict = dict(c)
        c_dict['post_title'] = post.get('title', '')
        all_comments.append(c_dict)

result = export_to_csv(all_comments, tmp_csv_comments)
check('Comments CSV export succeeds', result == True)

with open(tmp_csv_comments, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
check('Comments CSV has 4 rows', len(rows) == 4)
check('Comments CSV has post_title', 'post_title' in rows[0])
check('Comments CSV has author', rows[0].get('author') == 'Alice')
check('Comments CSV has is_reply', 'is_reply' in rows[0])

reply_rows = [r for r in rows if str(r.get('is_reply')) == '1']
check('CSV has 1 reply row', len(reply_rows) == 1)
check('Reply has parent_id', reply_rows[0].get('parent_id') == 'c1')
os.unlink(tmp_csv_comments)

# --- TC-08-8: JSON export with special characters ---
print('\n--- TC-08-8: Special characters ---')
tmp_json = tempfile.mktemp(suffix='.json')
special_data = {
    'title': '특수문자 <>&"\'',
    'content': 'Line1\nLine2\tTabbed',
    'emoji': '😀🎉',
    'path': 'C:\\Users\\test',
}
result = export_to_json(special_data, tmp_json)
check('Special chars JSON export', result == True)
with open(tmp_json, 'r', encoding='utf-8') as f:
    loaded = json.load(f)
check('Special chars preserved', loaded['title'] == '특수문자 <>&"\'')
check('Newlines preserved', '\n' in loaded['content'])
check('Backslash path preserved', loaded['path'] == 'C:\\Users\\test')
os.unlink(tmp_json)

# Cleanup
db.close()
os.unlink(db_path)

print(f'\n{"="*60}')
print(f'TOTAL: {passed} passed, {failed} failed')
print(f'{"="*60}')
