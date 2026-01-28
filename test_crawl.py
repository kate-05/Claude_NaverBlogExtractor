"""TC-02/05: Live crawling integration tests against a real Naver blog."""
import sys, os, tempfile
sys.path.insert(0, '.')

from pathlib import Path
from crawler.blog import BlogCrawler
from crawler.post import PostCrawler
from crawler.reaction import ReactionCrawler
from crawler.comment import CommentCrawler
from database.manager import DatabaseManager

passed = failed = 0
logs = []

def log_cb(msg):
    logs.append(msg)
    print(f'    LOG: {msg}')

def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f'  [PASS] {name}')
    else:
        failed += 1
        print(f'  [FAIL] {name}')

# Use a known small public blog
TEST_BLOG_ID = 'blogpeople'

print('=' * 60)
print('TC-02/05: LIVE CRAWLING INTEGRATION TESTS')
print(f'Target blog: {TEST_BLOG_ID}')
print('=' * 60)

# --- TC-05-1: BlogCrawler ---
print('\n--- TC-05-1: BlogCrawler.get_blog_info ---')
bc = BlogCrawler(progress_callback=log_cb)

info = bc.get_blog_info(TEST_BLOG_ID)
check('get_blog_info returns dict', info is not None and isinstance(info, dict))

if info:
    check('id present', 'id' in info and info['id'] == TEST_BLOG_ID)
    check('blog_name present and non-empty', 'blog_name' in info and len(info['blog_name']) > 0)
    check('author_name present', 'author_name' in info)
    check('url present', 'url' in info and 'naver.com' in info['url'])
    check('post_count is int', isinstance(info.get('post_count', 0), int))
    print(f'    => blog_name: {info["blog_name"]}')
    print(f'    => author_name: {info["author_name"]}')
    print(f'    => post_count: {info["post_count"]}')

# --- TC-05-2: PostCrawler - post list (limit to 1 page) ---
print('\n--- TC-05-2: PostCrawler.get_post_list ---')
pc = PostCrawler(progress_callback=log_cb)

# Only get first page (5 posts) to keep test fast
posts = pc._fetch_post_page(TEST_BLOG_ID, page=1, page_size=5)
check('get_post_list returns list', isinstance(posts, list))
check('At least 1 post found', len(posts) > 0)

test_log_no = None
test_post_id = None

if posts:
    p = posts[0]
    check('Post has id', 'id' in p and len(p['id']) > 0)
    check('Post has blog_id', p.get('blog_id') == TEST_BLOG_ID)
    check('Post has log_no', 'log_no' in p and len(p['log_no']) > 0)
    print(f'    => First post: id={p["id"]}, title={p.get("title", "N/A")[:50]}')
    print(f'    => Total posts retrieved: {len(posts)}')

    test_log_no = p['log_no']
    test_post_id = p['id']

# --- TC-05-3: PostCrawler - post content ---
if test_log_no:
    print('\n--- TC-05-3: PostCrawler.get_post_content ---')
    content = pc.get_post_content(TEST_BLOG_ID, test_log_no)
    check('get_post_content returns dict', content is not None and isinstance(content, dict))

    if content:
        check('Content has title key', 'title' in content)
        check('Content has content key', 'content' in content)
        check('Content has category key', 'category' in content)
        check('Content has post_date key', 'post_date' in content)
        has_data = content.get('title') is not None or content.get('content') is not None
        check('Has title or content data', has_data)
        print(f'    => title: {(content.get("title") or "N/A")[:60]}')
        print(f'    => content length: {len(content.get("content") or "")} chars')
        print(f'    => category: {content.get("category", "N/A")}')
        print(f'    => post_date: {content.get("post_date", "N/A")}')

# --- TC-05-4: ReactionCrawler ---
if test_log_no:
    print('\n--- TC-05-4: ReactionCrawler.get_reactions ---')
    rc = ReactionCrawler(progress_callback=log_cb)
    reactions = rc.get_reactions(TEST_BLOG_ID, test_log_no)
    check('get_reactions returns dict', reactions is not None and isinstance(reactions, dict))

    if reactions:
        check('Has total_count', 'total_count' in reactions)
        check('Has reactions list', 'reactions' in reactions and isinstance(reactions['reactions'], list))
        check('total_count is int', isinstance(reactions['total_count'], int))
        print(f'    => total_count: {reactions["total_count"]}')
        for r in reactions.get('reactions', []):
            print(f'    => {r["reaction_type"]}: {r["count"]}')

# --- TC-05-5: CommentCrawler ---
if test_log_no:
    print('\n--- TC-05-5: CommentCrawler.get_comments ---')
    cc = CommentCrawler(progress_callback=log_cb)
    comments = cc.get_comments(TEST_BLOG_ID, test_log_no)
    check('get_comments returns list', isinstance(comments, list))

    if comments:
        c0 = comments[0]
        check('Comment has id', 'id' in c0)
        check('Comment has post_id', 'post_id' in c0)
        check('Comment has author', 'author' in c0)
        check('Comment has content', 'content' in c0)
        check('Comment has like_count', 'like_count' in c0)
        check('Comment has is_reply field', 'is_reply' in c0)

        top_level = [c for c in comments if c['is_reply'] == 0]
        replies = [c for c in comments if c['is_reply'] == 1]
        print(f'    => Total: {len(comments)}, Top-level: {len(top_level)}, Replies: {len(replies)}')
        print(f'    => Sample: author={c0["author"]}, content={c0["content"][:50]}')
    else:
        print('    => No comments found (post may have comments disabled)')

# --- Full DB round-trip ---
if info and posts:
    print('\n--- Full DB integration: store & retrieve ---')
    db_path = Path(tempfile.mktemp(suffix='.db'))
    db = DatabaseManager(db_path)

    db.add_blog(TEST_BLOG_ID, info['blog_name'], info['url'],
                info.get('author_name'), len(posts))

    post_data = [{'id': p['id'], 'blog_id': TEST_BLOG_ID,
                  'title': p.get('title'), 'post_url': p.get('post_url')}
                 for p in posts]
    added = db.add_posts_batch(post_data)
    check(f'Stored {added} posts in DB', added == len(posts))

    stored_blog = db.get_blog(TEST_BLOG_ID)
    check('Blog retrievable from DB', stored_blog is not None)
    check('Blog name matches', stored_blog['blog_name'] == info['blog_name'])

    stored_posts = db.get_blog_posts(TEST_BLOG_ID)
    check('Posts retrievable from DB', len(stored_posts) == len(posts))

    db.close()
    os.unlink(db_path)

# --- TC-02-10: Nonexistent blog ---
print('\n--- TC-02-10: Nonexistent blog ---')
bad_info = bc.get_blog_info('this_blog_definitely_does_not_exist_xyz999')
check('Nonexistent blog handled gracefully',
      bad_info is None or isinstance(bad_info, dict))

print(f'\n{"="*60}')
print(f'TOTAL: {passed} passed, {failed} failed')
print(f'{"="*60}')
