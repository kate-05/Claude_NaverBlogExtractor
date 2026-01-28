"""TC-01/15: GUI structure and design consistency validation."""
import sys, os, inspect, ast, re
sys.path.insert(0, '.')

from datetime import datetime
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, APPEARANCE_MODE, COLOR_THEME,
    ACCESS_CODES, Status, CrawlStep
)

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
print('TC-01/15: GUI STRUCTURE & DESIGN VALIDATION')
print('=' * 60)

# --- TC-15-1: Config design parameters ---
print('\n--- TC-15-1: Config design parameters ---')
check('Window width 800', WINDOW_WIDTH == 800)
check('Window height 600', WINDOW_HEIGHT == 600)
check('Dark mode', APPEARANCE_MODE == 'dark')
check('Blue theme', COLOR_THEME == 'blue')

# --- TC-15-2: Source code structure validation ---
print('\n--- TC-15-2: Source code structure (AST analysis) ---')
with open('main.py', 'r', encoding='utf-8') as f:
    source = f.read()

tree = ast.parse(source)
classes = {node.name: node for node in ast.walk(tree)
           if isinstance(node, ast.ClassDef)}
functions = {node.name: node for node in ast.walk(tree)
             if isinstance(node, ast.FunctionDef)}

check('BlogListItem class exists', 'BlogListItem' in classes)
check('NaverBlogCrawlerApp class exists', 'NaverBlogCrawlerApp' in classes)
check('verify_access function exists', 'verify_access' in functions)
check('main function exists', 'main' in functions)

# Check NaverBlogCrawlerApp methods
app_class = classes['NaverBlogCrawlerApp']
app_methods = {node.name for node in ast.walk(app_class)
               if isinstance(node, ast.FunctionDef)}

required_methods = {
    '__init__', '_create_widgets', '_load_blogs', '_add_blog',
    '_add_blog_to_list', '_on_blog_select', '_on_blog_delete',
    '_start_crawling', '_pause_crawling', '_stop_crawling',
    '_crawl_blogs', '_export_data', '_log_message',
    '_process_message_queue', 'on_closing',
    '_check_incomplete_work',
}
for method in required_methods:
    check(f'App has method: {method}', method in app_methods)

# Check BlogListItem methods
bli_class = classes['BlogListItem']
bli_methods = {node.name for node in ast.walk(bli_class)
               if isinstance(node, ast.FunctionDef)}
check('BlogListItem has __init__', '__init__' in bli_methods)
check('BlogListItem has update_status', 'update_status' in bli_methods)
check('BlogListItem has _on_checkbox_change', '_on_checkbox_change' in bli_methods)
check('BlogListItem has _on_delete', '_on_delete' in bli_methods)

# --- TC-15-3: Widget creation validation ---
print('\n--- TC-15-3: Widget creation in source ---')
check('URL entry created', 'self.url_entry' in source)
check('Add button created', 'self.add_btn' in source)
check('Start button created', 'self.start_btn' in source)
check('Pause button created', 'self.pause_btn' in source)
check('Stop button created', 'self.stop_btn' in source)
check('Export button created', 'self.export_btn' in source)
check('Progress bar created', 'self.progress_bar' in source)
check('Progress label created', 'self.progress_label' in source)
check('Log text area created', 'self.log_text' in source)
check('Task label created', 'self.task_label' in source)
check('Blog list scrollable frame', 'CTkScrollableFrame' in source)
check('Main container frame', 'self.main_container' in source)

# --- TC-15-4: UI text (Korean labels) ---
print('\n--- TC-15-4: Korean UI labels ---')
check('Title label text', '네이버 블로그 크롤러' in source)
check('URL label text', '블로그 URL 입력' in source)
check('Add button text', '"추가"' in source)
check('Start button text', '"시작"' in source)
check('Pause button text', '"일시정지"' in source)
check('Stop button text', '"중단"' in source)
check('Export button text', '"내보내기"' in source)
check('Blog list label', '블로그 목록' in source)
check('Log label', '"로그:"' in source)
check('Progress label text', '전체 진행률' in source)

# --- TC-15-5: Layout uses pack (matching YTBExtractor) ---
print('\n--- TC-15-5: Layout system (pack-based) ---')
pack_count = source.count('.pack(')
grid_count = source.count('.grid(')
check(f'Uses pack layout ({pack_count} calls)', pack_count > 10)
check(f'No grid usage ({grid_count} calls)', grid_count == 0)

# --- TC-15-6: Thread safety (queue pattern) ---
print('\n--- TC-15-6: Thread safety ---')
check('Message queue imported', 'import queue' in source)
check('Queue created', 'queue.Queue()' in source)
check('message_queue.put used', 'self.message_queue.put' in source)
check('Threading imported', 'import threading' in source)
check('Thread daemon=True', 'daemon=True' in source)
check('after() for queue processing', 'self.after(' in source)

# --- TC-15-7: Font consistency ---
print('\n--- TC-15-7: Font and styling ---')
check('Title font size 20 bold',
      'font=ctk.CTkFont(size=20, weight="bold")' in source)
check('Uses CTk widgets', source.count('ctk.CTk') > 10)

# --- TC-01-1: Access code validation ---
print('\n--- TC-01-1: Access code validation ---')
check('Q1 code exists', 'KATE2026Q1' in ACCESS_CODES)
check('Q2 code exists', 'KATE2026Q2' in ACCESS_CODES)
check('Q3 code exists', 'KATE2026Q3' in ACCESS_CODES)
check('Q4 code exists', 'KATE2026Q4' in ACCESS_CODES)
check('4 access codes total', len(ACCESS_CODES) == 4)

# Verify Q1 is currently valid
q1_expiry = ACCESS_CODES['KATE2026Q1']
check('Q1 expiry is 2026-03-31', q1_expiry == '2026-03-31')
q1_date = datetime.strptime(q1_expiry, '%Y-%m-%d')
check('Q1 code currently valid', datetime.now() < q1_date)

# --- TC-01-2: verify_access code logic ---
print('\n--- TC-01-2: Access verification logic ---')
check('verify_access checks ACCESS_CODES', 'ACCESS_CODES.get(code)' in source)
check('Case-insensitive (upper)', '.upper()' in source)
check('Expiry check with strptime', 'strptime' in source)
check('Handles expired code', '만료된 코드' in source)
check('Handles invalid code', '유효하지 않은 코드' in source)
check('Enter key binding', '<Return>' in source)

# --- TC-01-3: Access dialog UI ---
print('\n--- TC-01-3: Access dialog structure ---')
check('Dialog title "인증"', '"인증"' in source)
check('Dialog geometry 350x180', '350x180' in source)
check('Placeholder text', 'KATE2026Q1' in source)
check('Centered on screen', 'winfo_screenwidth' in source)

# --- TC-15-8: Button states management ---
print('\n--- TC-15-8: Button state management ---')
check('Start btn disabled during crawl', 'self.start_btn.configure(state="disabled")' in source)
check('Pause btn enabled during crawl', 'self.pause_btn.configure(state="normal")' in source)
check('Stop btn enabled during crawl', 'self.stop_btn.configure(state="normal")' in source)
check('Buttons restored after crawl', 'crawl_finished' in source)

# --- TC-15-9: Window close handler ---
print('\n--- TC-15-9: Window close handling ---')
check('on_closing defined', 'def on_closing' in source)
check('WM_DELETE_WINDOW protocol', 'WM_DELETE_WINDOW' in source)
check('Save progress on close', 'save_progress' in source)
check('DB close on exit', 'self.db.close()' in source)
check('Confirm dialog on close during crawl', '크롤링이 진행 중' in source)

# --- TC-15-10: Crawl steps ---
print('\n--- TC-15-10: Crawl steps defined ---')
steps = CrawlStep.all_steps()
check('5 crawl steps', len(steps) == 5)
check('Step 1 blog_info', steps[0] == 'blog_info')
check('Step 2 post_list', steps[1] == 'post_list')
check('Step 3 post_content', steps[2] == 'post_content')
check('Step 4 reactions', steps[3] == 'reactions')
check('Step 5 comments', steps[4] == 'comments')

# --- TC-15-11: Status constants ---
print('\n--- TC-15-11: Status constants ---')
check('PENDING defined', Status.PENDING == 'pending')
check('IN_PROGRESS defined', Status.IN_PROGRESS == 'in_progress')
check('COMPLETED defined', Status.COMPLETED == 'completed')
check('FAILED defined', Status.FAILED == 'failed')

# --- TC-15-12: Module imports validation ---
print('\n--- TC-15-12: All modules importable ---')
try:
    from database import DatabaseManager
    check('database.DatabaseManager importable', True)
except ImportError:
    check('database.DatabaseManager importable', False)

try:
    from crawler import BlogCrawler, PostCrawler, ReactionCrawler, CommentCrawler
    check('All crawler classes importable', True)
except ImportError:
    check('All crawler classes importable', False)

try:
    from utils.helpers import (
        extract_blog_id, load_progress, save_progress,
        has_incomplete_work, update_blog_progress, get_blog_progress,
        get_next_incomplete_step, remove_blog_from_progress,
        export_to_json, export_to_csv
    )
    check('All helper functions importable', True)
except ImportError:
    check('All helper functions importable', False)

# --- TC-15-13: Delete button hover color ---
print('\n--- TC-15-13: Delete button styling ---')
check('Delete button X text', 'text="X"' in source)
check('Delete hover red', 'hover_color="#AA3333"' in source)
check('Delete transparent bg', 'fg_color="transparent"' in source)

# --- TC-15-14: Status formatting ---
print('\n--- TC-15-14: Status formatting ---')
check('Pending format', '대기중' in source)
check('In-progress format', '진행중' in source)
check('Completed format', '완료' in source)

print(f'\n{"="*60}')
print(f'TOTAL: {passed} passed, {failed} failed')
print(f'{"="*60}')
