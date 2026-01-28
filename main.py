"""Naver Blog Crawler - GUI Application using CustomTkinter."""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import queue
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, APPEARANCE_MODE, COLOR_THEME,
    DATABASE_PATH, EXPORT_DIR, Status, CrawlStep, ACCESS_CODES
)
from database import DatabaseManager
from crawler import BlogCrawler, PostCrawler, ReactionCrawler, CommentCrawler
from utils.helpers import (
    extract_blog_id, load_progress, save_progress, has_incomplete_work,
    update_blog_progress, get_blog_progress, get_next_incomplete_step,
    remove_blog_from_progress, export_to_json, export_to_csv
)


# Configure appearance
ctk.set_appearance_mode(APPEARANCE_MODE)
ctk.set_default_color_theme(COLOR_THEME)


class BlogListItem(ctk.CTkFrame):
    """Individual blog item in the list."""

    def __init__(self, parent, blog_data: Dict[str, Any],
                 on_select: callable = None, on_delete: callable = None):
        super().__init__(parent)

        self.blog_data = blog_data
        self.on_select = on_select
        self.on_delete = on_delete
        self.selected = False

        self.configure(fg_color="transparent")

        # Checkbox
        self.checkbox_var = ctk.BooleanVar(value=False)
        self.checkbox = ctk.CTkCheckBox(
            self, text="", variable=self.checkbox_var,
            width=20, command=self._on_checkbox_change
        )
        self.checkbox.pack(side="left", padx=(5, 10))

        # Blog name
        name = blog_data.get('blog_name', 'Unknown Blog')
        self.name_label = ctk.CTkLabel(self, text=name, anchor="w")
        self.name_label.pack(side="left", fill="x", expand=True)

        # Status
        status = blog_data.get('status', Status.PENDING)
        post_count = blog_data.get('post_count', 0)
        status_text = self._format_status(status, post_count)
        self.status_label = ctk.CTkLabel(self, text=status_text, width=150)
        self.status_label.pack(side="right", padx=5)

        # Delete button
        self.delete_btn = ctk.CTkButton(
            self, text="X", width=30, height=25,
            fg_color="transparent", hover_color="#AA3333",
            command=self._on_delete
        )
        self.delete_btn.pack(side="right", padx=5)

    def _format_status(self, status: str, post_count: int) -> str:
        """Format status text for display."""
        if status == Status.PENDING:
            return f"대기중 ({post_count}개)"
        elif status == Status.IN_PROGRESS:
            return "진행중"
        elif status == Status.COMPLETED:
            return f"완료 ({post_count}개)"
        return status

    def _on_checkbox_change(self):
        """Handle checkbox state change."""
        self.selected = self.checkbox_var.get()
        if self.on_select:
            self.on_select(self.blog_data['id'], self.selected)

    def _on_delete(self):
        """Handle delete button click."""
        if self.on_delete:
            self.on_delete(self.blog_data['id'])

    def update_status(self, status: str, progress_text: str = None):
        """Update the displayed status."""
        if progress_text:
            self.status_label.configure(text=progress_text)
        else:
            post_count = self.blog_data.get('post_count', 0)
            self.status_label.configure(
                text=self._format_status(status, post_count)
            )


class NaverBlogCrawlerApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("네이버 블로그 크롤러")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(600, 400)

        # Initialize components
        self.db = DatabaseManager(DATABASE_PATH)
        self.progress_data = load_progress()

        # Crawlers
        self.blog_crawler = BlogCrawler(progress_callback=self._log_message)
        self.post_crawler = PostCrawler(progress_callback=self._log_message)
        self.reaction_crawler = ReactionCrawler(progress_callback=self._log_message)
        self.comment_crawler = CommentCrawler(progress_callback=self._log_message)

        # State
        self.is_crawling = False
        self.should_stop = False
        self.selected_blogs = set()
        self.blog_widgets = {}

        # Message queue for thread-safe UI updates
        self.message_queue = queue.Queue()

        # Build UI
        self._create_widgets()

        # Load existing blogs
        self._load_blogs()

        # Check for incomplete work
        self.after(500, self._check_incomplete_work)

        # Process message queue
        self._process_message_queue()

    def _create_widgets(self):
        """Create all UI widgets."""
        # Main container
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        title_label = ctk.CTkLabel(
            self.main_container,
            text="네이버 블로그 크롤러",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(0, 15))

        # URL input section
        url_frame = ctk.CTkFrame(self.main_container)
        url_frame.pack(fill="x", pady=(0, 10))

        url_label = ctk.CTkLabel(url_frame, text="블로그 URL 입력:")
        url_label.pack(side="left", padx=5)

        self.url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="네이버 블로그 URL을 입력하세요"
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.url_entry.bind("<Return>", lambda e: self._add_blog())

        self.add_btn = ctk.CTkButton(
            url_frame, text="추가", width=80,
            command=self._add_blog
        )
        self.add_btn.pack(side="right", padx=5)

        # Blog list section
        list_label = ctk.CTkLabel(
            self.main_container, text="블로그 목록:", anchor="w"
        )
        list_label.pack(fill="x", pady=(10, 5))

        # Scrollable blog list
        self.blog_list_frame = ctk.CTkScrollableFrame(
            self.main_container, height=200
        )
        self.blog_list_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Progress section
        progress_frame = ctk.CTkFrame(self.main_container)
        progress_frame.pack(fill="x", pady=(0, 10))

        self.progress_label = ctk.CTkLabel(
            progress_frame, text="전체 진행률: 0%"
        )
        self.progress_label.pack(side="left", padx=10)

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=10)
        self.progress_bar.set(0)

        # Current task label
        self.task_label = ctk.CTkLabel(
            self.main_container,
            text="현재 작업: 대기 중",
            anchor="w"
        )
        self.task_label.pack(fill="x", pady=(0, 10))

        # Log area
        log_label = ctk.CTkLabel(
            self.main_container, text="로그:", anchor="w"
        )
        log_label.pack(fill="x")

        self.log_text = ctk.CTkTextbox(self.main_container, height=100)
        self.log_text.pack(fill="x", pady=(0, 10))

        # Button section
        button_frame = ctk.CTkFrame(
            self.main_container, fg_color="transparent"
        )
        button_frame.pack(fill="x")

        self.start_btn = ctk.CTkButton(
            button_frame, text="시작", width=100,
            command=self._start_crawling
        )
        self.start_btn.pack(side="left", padx=5)

        self.pause_btn = ctk.CTkButton(
            button_frame, text="일시정지", width=100,
            state="disabled", command=self._pause_crawling
        )
        self.pause_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            button_frame, text="중단", width=100,
            state="disabled", command=self._stop_crawling
        )
        self.stop_btn.pack(side="left", padx=5)

        self.export_btn = ctk.CTkButton(
            button_frame, text="내보내기", width=100,
            command=self._export_data
        )
        self.export_btn.pack(side="right", padx=5)

    def _load_blogs(self):
        """Load blogs from database and display them."""
        blogs = self.db.get_all_blogs()
        for blog in blogs:
            self._add_blog_to_list(blog)

    def _add_blog_to_list(self, blog_data: Dict[str, Any]):
        """Add a blog widget to the list."""
        blog_id = blog_data['id']

        # Remove existing if present
        if blog_id in self.blog_widgets:
            self.blog_widgets[blog_id].destroy()

        # Create new widget
        widget = BlogListItem(
            self.blog_list_frame,
            blog_data,
            on_select=self._on_blog_select,
            on_delete=self._on_blog_delete
        )
        widget.pack(fill="x", pady=2)

        self.blog_widgets[blog_id] = widget

    def _add_blog(self):
        """Add a new blog from URL input."""
        url = self.url_entry.get().strip()
        if not url:
            return

        # Extract blog ID from URL
        blog_id = extract_blog_id(url)
        if not blog_id:
            messagebox.showwarning(
                "경고", "올바른 네이버 블로그 URL을 입력해주세요."
            )
            return

        # Clear input
        self.url_entry.delete(0, "end")

        # Disable add button during fetch
        self.add_btn.configure(state="disabled")
        self._log_message(f"블로그 정보 가져오는 중: {blog_id}")

        # Fetch blog info in background
        def fetch_blog():
            blog_info = self.blog_crawler.get_blog_info(blog_id)

            if blog_info:
                success = self.db.add_blog(
                    blog_info['id'],
                    blog_info['blog_name'],
                    blog_info['url'],
                    author_name=blog_info.get('author_name'),
                    post_count=blog_info.get('post_count', 0)
                )

                if success:
                    self.message_queue.put(('add_blog', blog_info))
                    self.message_queue.put((
                        'log',
                        f"블로그 추가됨: {blog_info['blog_name']}"
                    ))
                else:
                    self.message_queue.put((
                        'log', "블로그가 이미 존재합니다."
                    ))
            else:
                self.message_queue.put((
                    'log',
                    f"블로그 정보를 가져올 수 없습니다: {blog_id}"
                ))

            self.message_queue.put(('enable_add', None))

        thread = threading.Thread(target=fetch_blog, daemon=True)
        thread.start()

    def _on_blog_select(self, blog_id: str, selected: bool):
        """Handle blog selection."""
        if selected:
            self.selected_blogs.add(blog_id)
        else:
            self.selected_blogs.discard(blog_id)

    def _on_blog_delete(self, blog_id: str):
        """Handle blog deletion."""
        if self.is_crawling:
            messagebox.showwarning(
                "경고", "크롤링 중에는 블로그를 삭제할 수 없습니다."
            )
            return

        if messagebox.askyesno(
            "확인", "이 블로그와 모든 관련 데이터를 삭제하시겠습니까?"
        ):
            self.db.delete_blog(blog_id)

            self.progress_data = remove_blog_from_progress(
                self.progress_data, blog_id
            )
            save_progress(self.progress_data)

            if blog_id in self.blog_widgets:
                self.blog_widgets[blog_id].destroy()
                del self.blog_widgets[blog_id]

            self.selected_blogs.discard(blog_id)
            self._log_message("블로그가 삭제되었습니다.")

    def _check_incomplete_work(self):
        """Check for incomplete work and offer to resume."""
        if has_incomplete_work(self.progress_data):
            result = messagebox.askyesno(
                "이어서 진행",
                "이전에 중단된 작업이 있습니다. 이어서 진행하시겠습니까?"
            )
            if result:
                self._start_crawling(resume=True)

    def _start_crawling(self, resume: bool = False):
        """Start the crawling process."""
        if self.is_crawling:
            return

        # Get blogs to crawl
        if resume:
            blogs_to_crawl = []
            for b_progress in self.progress_data.get('blogs', []):
                if b_progress.get('status') == 'in_progress':
                    blog = self.db.get_blog(b_progress['blog_id'])
                    if blog:
                        blogs_to_crawl.append(blog)
        else:
            if self.selected_blogs:
                blogs_to_crawl = [
                    self.db.get_blog(bid) for bid in self.selected_blogs
                    if self.db.get_blog(bid)
                ]
            else:
                blogs_to_crawl = [
                    b for b in self.db.get_all_blogs()
                    if b['status'] in [Status.PENDING, Status.IN_PROGRESS]
                ]

        if not blogs_to_crawl:
            messagebox.showinfo("알림", "크롤링할 블로그가 없습니다.")
            return

        # Update UI state
        self.is_crawling = True
        self.should_stop = False
        self.start_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal")
        self.stop_btn.configure(state="normal")
        self.add_btn.configure(state="disabled")

        # Start crawling in background
        thread = threading.Thread(
            target=self._crawl_blogs,
            args=(blogs_to_crawl, resume),
            daemon=True
        )
        thread.start()

    def _pause_crawling(self):
        """Pause the crawling process."""
        self.should_stop = True
        self._log_message(
            "일시정지 요청됨. 현재 작업 완료 후 중단됩니다..."
        )
        self.pause_btn.configure(state="disabled")

    def _stop_crawling(self):
        """Stop the crawling process."""
        self.should_stop = True
        self._log_message(
            "중단 요청됨. 현재 작업 완료 후 중단됩니다..."
        )
        self.stop_btn.configure(state="disabled")
        self.pause_btn.configure(state="disabled")

    def _crawl_blogs(self, blogs: List[Dict[str, Any]],
                     resume: bool = False):
        """Crawl multiple blogs (runs in background thread)."""
        total_blogs = len(blogs)

        for b_idx, blog in enumerate(blogs):
            if self.should_stop:
                break

            blog_id = blog['id']
            blog_name = blog['blog_name']

            self.message_queue.put((
                'log', f"블로그 크롤링 시작: {blog_name}"
            ))
            self.message_queue.put((
                'update_blog_status',
                (blog_id, Status.IN_PROGRESS, "진행중")
            ))

            self.db.update_blog_status(blog_id, Status.IN_PROGRESS)

            # Get or create progress
            b_progress = get_blog_progress(self.progress_data, blog_id)
            if not b_progress:
                self.progress_data = update_blog_progress(
                    self.progress_data, blog_id,
                    blog_name=blog_name,
                    status='in_progress',
                    total_posts=blog.get('post_count', 0)
                )
                b_progress = get_blog_progress(self.progress_data, blog_id)

            # Process each step
            success = True
            for step in CrawlStep.all_steps():
                if self.should_stop:
                    break

                # Skip completed steps when resuming
                if (resume and
                        b_progress['steps_completed'].get(step) == 'completed'):
                    continue

                self.message_queue.put((
                    'task', f"현재 작업: {self._get_step_name(step)}"
                ))

                # Mark step as in progress
                self.progress_data = update_blog_progress(
                    self.progress_data, blog_id,
                    step=step, step_status='in_progress'
                )
                save_progress(self.progress_data)

                # Execute step
                try:
                    if step == CrawlStep.BLOG_INFO:
                        success = self._process_blog_info(blog)
                    elif step == CrawlStep.POST_LIST:
                        success = self._process_post_list(blog)
                    elif step == CrawlStep.POST_CONTENT:
                        success = self._process_post_content(
                            blog, b_progress
                        )
                    elif step == CrawlStep.REACTIONS:
                        success = self._process_reactions(blog)
                    elif step == CrawlStep.COMMENTS:
                        success = self._process_comments(blog)

                    if success and not self.should_stop:
                        self.progress_data = update_blog_progress(
                            self.progress_data, blog_id,
                            step=step, step_status='completed'
                        )
                        save_progress(self.progress_data)

                except Exception as e:
                    self.message_queue.put((
                        'log', f"오류 발생: {str(e)}"
                    ))
                    success = False
                    break

            # Update blog status
            if success and not self.should_stop:
                self.db.update_blog_status(blog_id, Status.COMPLETED)
                self.progress_data = update_blog_progress(
                    self.progress_data, blog_id, status='completed'
                )
                self.message_queue.put((
                    'update_blog_status',
                    (blog_id, Status.COMPLETED, None)
                ))
                self.message_queue.put((
                    'log', f"블로그 크롤링 완료: {blog_name}"
                ))
            else:
                self.message_queue.put((
                    'log', f"블로그 크롤링 중단됨: {blog_name}"
                ))

            save_progress(self.progress_data)

            # Update overall progress
            progress = (b_idx + 1) / total_blogs
            self.message_queue.put(('progress', progress))

        # Crawling finished
        self.message_queue.put(('crawl_finished', None))

    def _process_blog_info(self, blog: Dict[str, Any]) -> bool:
        """Process blog info step."""
        blog_id = blog['id']

        blog_info = self.blog_crawler.get_blog_info(blog_id)
        if blog_info:
            self.db.update_blog_info(
                blog_id,
                blog_name=blog_info.get('blog_name'),
                author_name=blog_info.get('author_name')
            )
            self.message_queue.put((
                'log',
                f"블로그 정보 수집 완료: {blog_info.get('blog_name')}"
            ))
            return True

        return False

    def _process_post_list(self, blog: Dict[str, Any]) -> bool:
        """Process post list step."""
        blog_id = blog['id']

        self.message_queue.put(('log', "글 목록 가져오는 중..."))

        posts = self.post_crawler.get_post_list(blog_id)

        if posts:
            post_data = [
                {
                    'id': p['id'],
                    'blog_id': blog_id,
                    'title': p.get('title'),
                    'post_url': p.get('post_url'),
                }
                for p in posts
            ]
            added = self.db.add_posts_batch(post_data)

            self.db.update_blog_post_count(blog_id, len(posts))

            self.progress_data = update_blog_progress(
                self.progress_data, blog_id,
                total_posts=len(posts)
            )

            self.message_queue.put((
                'log', f"글 {added}개 추가됨"
            ))
            return True

        self.message_queue.put(('log', "글 목록을 가져올 수 없습니다."))
        return False

    def _process_post_content(self, blog: Dict[str, Any],
                              b_progress: Dict[str, Any]) -> bool:
        """Process post content step."""
        blog_id = blog['id']
        posts = self.db.get_posts_by_status(
            blog_id, crawl_status=Status.PENDING
        )

        if not posts:
            return True

        total = len(posts)
        start_index = b_progress.get('current_post_index', 0)

        self.message_queue.put((
            'log', f"글 내용 수집 중... ({total}개 글)"
        ))

        for i, post in enumerate(posts[start_index:], start=start_index):
            if self.should_stop:
                break

            # Extract log_no from post id (format: blogId_logNo)
            log_no = post['id'].split('_', 1)[-1] if '_' in post['id'] else post['id']

            content_data = self.post_crawler.get_post_content(
                blog_id, log_no
            )

            if content_data:
                self.db.update_post_content(
                    post['id'],
                    title=content_data.get('title'),
                    content=content_data.get('content'),
                    category=content_data.get('category'),
                    post_date=content_data.get('post_date')
                )
                self.db.update_post_crawl_status(
                    post['id'], Status.COMPLETED
                )
            else:
                self.db.update_post_crawl_status(
                    post['id'], Status.UNAVAILABLE
                )

            # Update progress
            self.progress_data = update_blog_progress(
                self.progress_data, blog_id,
                current_post_index=i + 1
            )
            save_progress(self.progress_data)

            # Update UI
            progress_text = f"진행중 ({i + 1}/{total})"
            self.message_queue.put((
                'update_blog_status',
                (blog_id, Status.IN_PROGRESS, progress_text)
            ))
            self.message_queue.put(('progress', (i + 1) / total))

        return not self.should_stop

    def _process_reactions(self, blog: Dict[str, Any]) -> bool:
        """Process reactions step."""
        blog_id = blog['id']
        posts = self.db.get_blog_posts(blog_id)

        if not posts:
            return True

        total = len(posts)
        self.message_queue.put((
            'log', f"공감 수집 중... ({total}개 글)"
        ))

        for i, post in enumerate(posts):
            if self.should_stop:
                break

            log_no = post['id'].split('_', 1)[-1] if '_' in post['id'] else post['id']

            reaction_data = self.reaction_crawler.get_reactions(
                blog_id, log_no
            )

            if reaction_data:
                total_count = reaction_data.get('total_count', 0)
                self.db.update_post_sympathy_count(post['id'], total_count)

                for reaction in reaction_data.get('reactions', []):
                    self.db.add_reaction(
                        post['id'],
                        reaction['reaction_type'],
                        reaction['count']
                    )

            # Update UI
            progress_text = f"공감 ({i + 1}/{total})"
            self.message_queue.put((
                'update_blog_status',
                (blog_id, Status.IN_PROGRESS, progress_text)
            ))
            self.message_queue.put(('progress', (i + 1) / total))

        return not self.should_stop

    def _process_comments(self, blog: Dict[str, Any]) -> bool:
        """Process comments step."""
        blog_id = blog['id']
        posts = self.db.get_blog_posts(blog_id)

        if not posts:
            return True

        total = len(posts)
        self.message_queue.put((
            'log', f"댓글 수집 중... ({total}개 글)"
        ))

        for i, post in enumerate(posts):
            if self.should_stop:
                break

            log_no = post['id'].split('_', 1)[-1] if '_' in post['id'] else post['id']

            comments = self.comment_crawler.get_comments(blog_id, log_no)

            if comments:
                self.db.add_comments_batch(comments)
                self.db.update_post_comment_count(
                    post['id'], len(comments)
                )

            # Update UI
            progress_text = f"댓글 ({i + 1}/{total})"
            self.message_queue.put((
                'update_blog_status',
                (blog_id, Status.IN_PROGRESS, progress_text)
            ))
            self.message_queue.put(('progress', (i + 1) / total))

        return not self.should_stop

    def _get_step_name(self, step: str) -> str:
        """Get Korean name for step."""
        names = {
            CrawlStep.BLOG_INFO: "블로그 정보 수집",
            CrawlStep.POST_LIST: "글 목록 수집",
            CrawlStep.POST_CONTENT: "글 내용 수집",
            CrawlStep.REACTIONS: "공감 수집",
            CrawlStep.COMMENTS: "댓글 수집",
        }
        return names.get(step, step)

    def _export_data(self):
        """Export crawled data."""
        blogs = self.db.get_all_blogs()
        completed = [b for b in blogs if b['status'] == Status.COMPLETED]

        if not completed:
            messagebox.showinfo(
                "알림", "내보낼 수 있는 완료된 블로그가 없습니다."
            )
            return

        # Create export directory
        os.makedirs(EXPORT_DIR, exist_ok=True)

        # Ask for export format
        export_format = messagebox.askquestion(
            "내보내기 형식",
            "JSON 형식으로 내보내시겠습니까? (아니오를 선택하면 CSV)"
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for blog in completed:
            blog_id = blog['id']
            # Windows 파일명에 사용 불가한 문자 제거: < > : " / \ | ? *
            blog_name = blog['blog_name']
            for char in ['/', '\\', '|', '<', '>', ':', '"', '?', '*']:
                blog_name = blog_name.replace(char, '_')

            posts = self.db.get_blog_posts(blog_id)

            if export_format == 'yes':
                # JSON export
                data = {
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
                    post_data['reactions'] = self.db.get_reactions(post['id'])
                    comments = self.db.get_comments(post['id'])

                    # Structure comments with replies nested
                    top_comments = []
                    reply_map = {}
                    for c in comments:
                        c_dict = dict(c)
                        if c['is_reply'] and c.get('parent_id'):
                            reply_map.setdefault(
                                c['parent_id'], []
                            ).append(c_dict)
                        else:
                            c_dict['replies'] = []
                            top_comments.append(c_dict)

                    for tc in top_comments:
                        tc['replies'] = reply_map.get(tc['id'], [])

                    post_data['comments'] = top_comments
                    data['posts'].append(post_data)

                filepath = EXPORT_DIR / f"{blog_name}_{timestamp}.json"
                export_to_json(data, str(filepath))

            else:
                # CSV export - posts
                posts_csv = []
                for p in posts:
                    p_dict = dict(p)
                    p_dict['blog_name'] = blog['blog_name']
                    p_dict['author_name'] = blog.get('author_name', '')
                    posts_csv.append(p_dict)

                filepath = EXPORT_DIR / f"{blog_name}_posts_{timestamp}.csv"
                export_to_csv(posts_csv, str(filepath))

                # CSV export - comments
                all_comments = []
                for post in posts:
                    comments = self.db.get_comments(post['id'])
                    for c in comments:
                        c_dict = dict(c)
                        c_dict['post_title'] = post.get('title', '')
                        all_comments.append(c_dict)

                if all_comments:
                    comments_path = (
                        EXPORT_DIR / f"{blog_name}_comments_{timestamp}.csv"
                    )
                    export_to_csv(all_comments, str(comments_path))

        self._log_message(f"데이터 내보내기 완료: {EXPORT_DIR}")
        messagebox.showinfo(
            "완료", f"데이터가 {EXPORT_DIR}에 저장되었습니다."
        )

    def _log_message(self, message: str):
        """Log a message (thread-safe)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.message_queue.put(('log', f"[{timestamp}] {message}"))

    def _process_message_queue(self):
        """Process messages from background threads."""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()

                if msg_type == 'log':
                    self.log_text.insert("end", f"{data}\n")
                    self.log_text.see("end")

                elif msg_type == 'progress':
                    self.progress_bar.set(data)
                    self.progress_label.configure(
                        text=f"전체 진행률: {int(data * 100)}%"
                    )

                elif msg_type == 'task':
                    self.task_label.configure(text=data)

                elif msg_type == 'add_blog':
                    blog_data = data
                    self._add_blog_to_list(blog_data)

                elif msg_type == 'enable_add':
                    self.add_btn.configure(state="normal")

                elif msg_type == 'update_blog_status':
                    blog_id, status, progress_text = data
                    if blog_id in self.blog_widgets:
                        self.blog_widgets[blog_id].update_status(
                            status, progress_text
                        )

                elif msg_type == 'crawl_finished':
                    self.is_crawling = False
                    self.should_stop = False
                    self.start_btn.configure(state="normal")
                    self.pause_btn.configure(state="disabled")
                    self.stop_btn.configure(state="disabled")
                    self.add_btn.configure(state="normal")
                    self.task_label.configure(text="현재 작업: 대기 중")

        except queue.Empty:
            pass

        # Schedule next check
        self.after(100, self._process_message_queue)

    def on_closing(self):
        """Handle window close event."""
        from crawler.selenium_helper import close_shared_driver

        if self.is_crawling:
            if messagebox.askyesno(
                "확인", "크롤링이 진행 중입니다. 종료하시겠습니까?"
            ):
                self.should_stop = True
                save_progress(self.progress_data)
                self.db.close()
                close_shared_driver()
                self.destroy()
        else:
            self.db.close()
            close_shared_driver()
            self.destroy()


def verify_access() -> bool:
    """Verify access code before starting the application."""
    dialog = ctk.CTk()
    dialog.title("인증")
    dialog.geometry("350x180")
    dialog.resizable(False, False)

    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - 350) // 2
    y = (dialog.winfo_screenheight() - 180) // 2
    dialog.geometry(f"350x180+{x}+{y}")

    result = {"verified": False}

    # Label
    label = ctk.CTkLabel(
        dialog, text="액세스 코드를 입력하세요", font=("", 14)
    )
    label.pack(pady=(20, 10))

    # Entry
    code_entry = ctk.CTkEntry(
        dialog, width=250, placeholder_text="예: KATE2026Q1"
    )
    code_entry.pack(pady=10)
    code_entry.focus()

    # Status label
    status_label = ctk.CTkLabel(dialog, text="", text_color="red")
    status_label.pack(pady=5)

    def check_code(event=None):
        code = code_entry.get().strip().upper()

        if not code:
            status_label.configure(text="코드를 입력해주세요")
            return

        expiry = ACCESS_CODES.get(code)

        if not expiry:
            status_label.configure(text="유효하지 않은 코드입니다")
            return

        expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
        if datetime.now() > expiry_date:
            status_label.configure(
                text=f"만료된 코드입니다 (만료일: {expiry})"
            )
            return

        result["verified"] = True
        dialog.destroy()

    # Bind Enter key
    code_entry.bind("<Return>", check_code)

    # Button
    btn = ctk.CTkButton(
        dialog, text="확인", command=check_code, width=100
    )
    btn.pack(pady=10)

    # Handle window close
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

    dialog.mainloop()

    return result["verified"]


def main():
    """Main entry point."""
    if not verify_access():
        return

    app = NaverBlogCrawlerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
