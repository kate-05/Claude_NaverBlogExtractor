"""TC-11: Database integrity tests."""
import sys, os, tempfile
sys.path.insert(0, '.')

from pathlib import Path
from database.manager import DatabaseManager
from config import Status

db_path = Path(tempfile.mktemp(suffix='.db'))
db = DatabaseManager(db_path)

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
print('TC-11: DATABASE INTEGRITY TESTS')
print('=' * 60)

# --- Blog CRUD ---
print('\n--- Blog CRUD ---')
r = db.add_blog('blog1', 'Test Blog', 'https://blog.naver.com/blog1', 'Author1', 10)
check('Add blog', r == True)

r = db.add_blog('blog1', 'Dup', 'url', 'Dup')
check('Add duplicate blog returns False', r == False)

b = db.get_blog('blog1')
check('Get blog by ID', b is not None and b['blog_name'] == 'Test Blog')
check('Author name stored', b['author_name'] == 'Author1')
check('Post count stored', b['post_count'] == 10)
check('Status default PENDING', b['status'] == Status.PENDING)

blogs = db.get_all_blogs()
check('Get all blogs returns list', len(blogs) == 1)

r = db.update_blog_status('blog1', Status.IN_PROGRESS)
check('Update blog status', r == True)
b = db.get_blog('blog1')
check('Status updated to IN_PROGRESS', b['status'] == Status.IN_PROGRESS)

r = db.update_blog_info('blog1', blog_name='Updated Name', author_name='New Author')
check('Update blog info', r == True)
b = db.get_blog('blog1')
check('Blog name updated', b['blog_name'] == 'Updated Name')
check('Author updated', b['author_name'] == 'New Author')

r = db.update_blog_post_count('blog1', 25)
check('Update post count', r == True)

r = db.update_blog_info('blog1')
check('Update blog info with no params returns False', r == False)

# --- Post CRUD ---
print('\n--- Post CRUD ---')
r = db.add_post('blog1_001', 'blog1', 'Post 1', 'https://url1')
check('Add post', r == True)

r = db.add_post('blog1_001', 'blog1', 'Dup', 'url')
check('Add duplicate post returns False', r == False)

batch = [
    {'id': 'blog1_002', 'blog_id': 'blog1', 'title': 'Post 2', 'post_url': 'url2'},
    {'id': 'blog1_003', 'blog_id': 'blog1', 'title': 'Post 3', 'post_url': 'url3'},
    {'id': 'blog1_001', 'blog_id': 'blog1', 'title': 'Dup', 'post_url': 'dup'},
]
added = db.add_posts_batch(batch)
check('Batch add posts (skip dup)', added == 2)

posts = db.get_blog_posts('blog1')
check('Get all posts for blog', len(posts) == 3)

r = db.update_post_content('blog1_001', title='Updated Title', content='Hello world',
                           category='Tech', post_date='2026-01-27')
check('Update post content', r == True)
p = db.get_post('blog1_001')
check('Post title updated', p['title'] == 'Updated Title')
check('Post content stored', p['content'] == 'Hello world')
check('Post category stored', p['category'] == 'Tech')

r = db.update_post_crawl_status('blog1_001', Status.COMPLETED)
check('Update crawl status', r == True)

pending = db.get_posts_by_status('blog1', crawl_status=Status.PENDING)
check('Get pending posts', len(pending) == 2)

completed = db.get_posts_by_status('blog1', crawl_status=Status.COMPLETED)
check('Get completed posts', len(completed) == 1)

r = db.update_post_sympathy_count('blog1_001', 42)
check('Update sympathy count', r == True)
p = db.get_post('blog1_001')
check('Sympathy count stored', p['sympathy_count'] == 42)

r = db.update_post_comment_count('blog1_001', 15)
check('Update comment count', r == True)
p = db.get_post('blog1_001')
check('Comment count stored', p['comment_count'] == 15)

# --- Reaction CRUD ---
print('\n--- Reaction CRUD ---')
r = db.add_reaction('blog1_001', 'like', 30)
check('Add reaction', r == True)

r = db.add_reaction('blog1_001', 'fun', 12)
check('Add second reaction type', r == True)

r = db.add_reaction('blog1_001', 'like', 35)
check('Update existing reaction (REPLACE)', r == True)

reactions = db.get_reactions('blog1_001')
check('Get reactions count', len(reactions) == 2)
like_r = [r for r in reactions if r['reaction_type'] == 'like'][0]
check('Reaction count updated to 35', like_r['count'] == 35)

batch_r = [
    {'post_id': 'blog1_002', 'reaction_type': 'sympathy', 'count': 5},
    {'post_id': 'blog1_002', 'reaction_type': 'useful', 'count': 3},
]
added = db.add_reactions_batch(batch_r)
check('Batch add reactions', added == 2)

# --- Comment CRUD ---
print('\n--- Comment CRUD ---')
r = db.add_comment('c1', 'blog1_001', 'User A', 'Nice post!', 5, '2026-01-27', is_reply=0)
check('Add top-level comment', r == True)

r = db.add_comment('c2', 'blog1_001', 'User B', 'Thanks!', 2, '2026-01-28',
                   parent_id='c1', is_reply=1)
check('Add reply comment', r == True)

r = db.add_comment('c3', 'blog1_001', 'User C', 'Great!', 0, '2026-01-29', is_reply=0)
check('Add another top-level comment', r == True)

all_comments = db.get_comments('blog1_001', include_replies=True)
check('Get all comments with replies', len(all_comments) == 3)

top_only = db.get_comments('blog1_001', include_replies=False)
check('Get top-level comments only', len(top_only) == 2)

count = db.get_comment_count('blog1_001')
check('Comment count', count == 3)

reply = [c for c in all_comments if c['is_reply'] == 1][0]
check('Reply parent_id is correct', reply['parent_id'] == 'c1')
check('Reply like_count stored', reply['like_count'] == 2)

# Batch comments
batch_c = [
    {'id': 'c4', 'post_id': 'blog1_002', 'author': 'X', 'content': 'Y',
     'like_count': 0, 'written_at': '2026-01-27', 'is_reply': 0},
    {'id': 'c5', 'post_id': 'blog1_002', 'parent_id': 'c4', 'author': 'Z', 'content': 'W',
     'like_count': 1, 'written_at': '2026-01-28', 'is_reply': 1},
]
added = db.add_comments_batch(batch_c)
check('Batch add comments', added == 2)

# --- TC-11-1: Comment-reply FK integrity ---
print('\n--- TC-11-1: Comment-reply FK integrity ---')
all_ids = {c['id'] for c in all_comments}
invalid_parents = [c for c in all_comments
                   if c['is_reply'] == 1
                   and c['parent_id'] not in all_ids]
check('All reply parent_ids are valid', len(invalid_parents) == 0)

# --- TC-11-3: Post-blog FK integrity ---
print('\n--- TC-11-3: Post-blog FK integrity ---')
all_posts = db.get_blog_posts('blog1')
check('All posts belong to valid blog', all(p['blog_id'] == 'blog1' for p in all_posts))

# --- TC-11-4: Cascade delete ---
print('\n--- TC-11-4: Cascade delete ---')
db.add_blog('blog2', 'Blog 2', 'url2')
db.add_post('blog2_001', 'blog2', 'P1')
db.add_comment('c10', 'blog2_001', 'X', 'Y')
db.add_reaction('blog2_001', 'like', 5)

r = db.delete_blog('blog2')
check('Delete blog returns True', r == True)
check('Blog deleted', db.get_blog('blog2') is None)
check('Posts deleted', len(db.get_blog_posts('blog2')) == 0)
check('Reactions cleaned up', len(db.get_reactions('blog2_001')) == 0)
check('Comments cleaned up', len(db.get_comments('blog2_001')) == 0)
check('Blog1 still exists', db.get_blog('blog1') is not None)
check('Blog1 posts unaffected', len(db.get_blog_posts('blog1')) == 3)

# --- Progress ---
print('\n--- Progress CRUD ---')
r = db.init_progress('blog1', 25)
check('Init progress', r == True)

prog = db.get_progress('blog1')
check('Get progress', prog is not None)
check('Progress total_posts', prog['total_posts'] == 25)

r = db.update_progress('blog1', current_post_index=10, current_step='post_content')
check('Update progress', r == True)
prog = db.get_progress('blog1')
check('Progress index updated', prog['current_post_index'] == 10)
check('Progress step updated', prog['current_step'] == 'post_content')

# --- Stats ---
print('\n--- Blog Stats ---')
stats = db.get_blog_stats('blog1')
check('Stats total_posts', stats['total_posts'] == 3)
check('Stats posts_completed', stats['posts_completed'] == 1)
check('Stats total_comments (3+2 batch)', stats['total_comments'] == 5)

db.close()
os.unlink(db_path)

print(f'\n{"="*60}')
print(f'TOTAL: {passed} passed, {failed} failed')
print(f'{"="*60}')
