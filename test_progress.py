"""TC-07: Progress save/load/resume tests."""
import sys, os, tempfile, json
sys.path.insert(0, '.')

from pathlib import Path
from utils.helpers import (
    load_progress, save_progress, has_incomplete_work,
    get_blog_progress, update_blog_progress,
    remove_blog_from_progress, get_next_incomplete_step
)
from config import CrawlStep

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
print('TC-07: PROGRESS SAVE/LOAD/RESUME TESTS')
print('=' * 60)

# Use temp files
tmp = tempfile.mktemp(suffix='.json')
progress_path = Path(tmp)

# --- TC-07-5: File does not exist ---
print('\n--- TC-07-5: Progress file missing ---')
data = load_progress(progress_path)
check('Load nonexistent returns default', data == {'last_updated': None, 'blogs': []})
check('has_incomplete_work on empty', has_incomplete_work(data) == False)

# --- Basic save/load ---
print('\n--- Save/Load cycle ---')
data = update_blog_progress(data, 'blog1', blog_name='Test Blog',
                            status='in_progress', total_posts=50)
r = save_progress(data, progress_path)
check('Save progress returns True', r == True)
check('File created', os.path.exists(progress_path))

loaded = load_progress(progress_path)
check('Load returns saved data', len(loaded['blogs']) == 1)
check('Blog ID preserved', loaded['blogs'][0]['blog_id'] == 'blog1')
check('Blog name preserved', loaded['blogs'][0]['blog_name'] == 'Test Blog')
check('Status preserved', loaded['blogs'][0]['status'] == 'in_progress')
check('Total posts preserved', loaded['blogs'][0]['total_posts'] == 50)
check('last_updated set', loaded['last_updated'] is not None)

# --- get_blog_progress ---
print('\n--- get_blog_progress ---')
bp = get_blog_progress(loaded, 'blog1')
check('Get existing blog progress', bp is not None)
check('Blog progress has steps', 'steps_completed' in bp)

bp_none = get_blog_progress(loaded, 'nonexistent')
check('Get nonexistent blog returns None', bp_none is None)

# --- has_incomplete_work ---
print('\n--- has_incomplete_work ---')
check('In-progress blog detected', has_incomplete_work(loaded) == True)

# Complete all steps for blog1
for step in CrawlStep.all_steps():
    loaded = update_blog_progress(loaded, 'blog1', step=step, step_status='completed')
loaded = update_blog_progress(loaded, 'blog1', status='completed')
check('All steps completed, status completed => no incomplete', has_incomplete_work(loaded) == False)

# Add a blog with pending step
loaded = update_blog_progress(loaded, 'blog2', blog_name='Blog 2',
                              status='pending', total_posts=10)
check('Pending steps detected', has_incomplete_work(loaded) == True)

# --- get_next_incomplete_step ---
print('\n--- get_next_incomplete_step ---')
bp1 = get_blog_progress(loaded, 'blog1')
check('All completed => next step is None', get_next_incomplete_step(bp1) is None)

bp2 = get_blog_progress(loaded, 'blog2')
next_step = get_next_incomplete_step(bp2)
check('Pending blog => first step', next_step == CrawlStep.BLOG_INFO)

# Simulate partial progress
loaded = update_blog_progress(loaded, 'blog2', step=CrawlStep.BLOG_INFO, step_status='completed')
loaded = update_blog_progress(loaded, 'blog2', step=CrawlStep.POST_LIST, step_status='completed')
loaded = update_blog_progress(loaded, 'blog2', step=CrawlStep.POST_CONTENT, step_status='in_progress')
bp2 = get_blog_progress(loaded, 'blog2')
next_step = get_next_incomplete_step(bp2)
check('In-progress step returned first', next_step == CrawlStep.POST_CONTENT)

# After completing POST_CONTENT
loaded = update_blog_progress(loaded, 'blog2', step=CrawlStep.POST_CONTENT, step_status='completed')
bp2 = get_blog_progress(loaded, 'blog2')
next_step = get_next_incomplete_step(bp2)
check('Next pending step is REACTIONS', next_step == CrawlStep.REACTIONS)

# --- update_blog_progress: current_post_index ---
print('\n--- current_post_index tracking ---')
loaded = update_blog_progress(loaded, 'blog2', current_post_index=25)
bp2 = get_blog_progress(loaded, 'blog2')
check('Post index updated to 25', bp2['current_post_index'] == 25)

loaded = update_blog_progress(loaded, 'blog2', current_post_index=30)
bp2 = get_blog_progress(loaded, 'blog2')
check('Post index updated to 30', bp2['current_post_index'] == 30)

# --- remove_blog_from_progress ---
print('\n--- remove_blog_from_progress ---')
loaded = remove_blog_from_progress(loaded, 'blog2')
check('Blog2 removed', get_blog_progress(loaded, 'blog2') is None)
check('Blog1 still present', get_blog_progress(loaded, 'blog1') is not None)
check('Blogs list shrunk', len(loaded['blogs']) == 1)

# Remove nonexistent blog (should not error)
loaded = remove_blog_from_progress(loaded, 'nonexistent')
check('Remove nonexistent does not error', len(loaded['blogs']) == 1)

# --- TC-07-4: Corrupted progress file ---
print('\n--- TC-07-4: Corrupted progress file ---')
with open(progress_path, 'w') as f:
    f.write('NOT VALID JSON {{{')
corrupted = load_progress(progress_path)
check('Corrupted file returns default', corrupted == {'last_updated': None, 'blogs': []})

# --- TC-07-4b: Empty file ---
with open(progress_path, 'w') as f:
    f.write('')
empty = load_progress(progress_path)
check('Empty file returns default', empty == {'last_updated': None, 'blogs': []})

# --- Multiple blogs resume scenario ---
print('\n--- TC-07-6: Multiple blog resume ---')
data = {'last_updated': None, 'blogs': []}
data = update_blog_progress(data, 'a', blog_name='A', status='in_progress', total_posts=10)
data = update_blog_progress(data, 'a', step=CrawlStep.BLOG_INFO, step_status='completed')
data = update_blog_progress(data, 'a', step=CrawlStep.POST_LIST, step_status='completed')
data = update_blog_progress(data, 'a', step=CrawlStep.POST_CONTENT, step_status='in_progress')

data = update_blog_progress(data, 'b', blog_name='B', status='in_progress', total_posts=20)
data = update_blog_progress(data, 'b', step=CrawlStep.BLOG_INFO, step_status='completed')

check('Two in-progress blogs', has_incomplete_work(data) == True)
in_progress = [b for b in data['blogs'] if b['status'] == 'in_progress']
check('Both blogs in-progress', len(in_progress) == 2)

bp_a = get_blog_progress(data, 'a')
check('Blog A next step POST_CONTENT', get_next_incomplete_step(bp_a) == CrawlStep.POST_CONTENT)

bp_b = get_blog_progress(data, 'b')
check('Blog B next step POST_LIST', get_next_incomplete_step(bp_b) == CrawlStep.POST_LIST)

# Cleanup
os.unlink(progress_path)

print(f'\n{"="*60}')
print(f'TOTAL: {passed} passed, {failed} failed')
print(f'{"="*60}')
