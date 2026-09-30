"""Dependency-free content/asset regression checks: python3 tests/check_site.py."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import unittest

ROOT = Path(__file__).resolve().parents[1]

class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = []
    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))

class PortfolioChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'index.html').read_text()
        cls.parser = SiteParser()
        cls.parser.feed(cls.html)
        cls.nodes = cls.parser.nodes

    def test_unique_ids_and_single_primary_heading(self):
        ids = [a['id'] for _, a in self.nodes if 'id' in a]
        self.assertFalse([value for value, count in Counter(ids).items() if count > 1])
        self.assertEqual(sum(tag == 'h1' for tag, _ in self.nodes), 1)

    def test_every_anchor_has_a_target(self):
        ids = {a['id'] for _, a in self.nodes if 'id' in a}
        for tag, attrs in self.nodes:
            if tag == 'a' and attrs.get('href', '').startswith('#'):
                self.assertIn(attrs['href'][1:], ids)

    def test_local_assets_exist(self):
        for tag, attrs in self.nodes:
            source = attrs.get('src') if tag in ('img', 'script') else attrs.get('href') if tag == 'link' else None
            if source and not urlsplit(source).scheme:
                self.assertTrue((ROOT / urlsplit(source).path).is_file(), source)

    def test_only_three_requested_projects(self):
        projects = [attrs['id'] for _, attrs in self.nodes if 'data-type' in attrs]
        self.assertEqual(projects, ['project-dekk', 'project-learnflow', 'project-vench'])
        self.assertNotIn('Emori', self.html)
        self.assertNotIn('coupang-data', self.html)

    def test_share_preview_uses_a_dedicated_banner(self):
        meta = {attrs.get('property', attrs.get('name')): attrs.get('content')
                for tag, attrs in self.nodes if tag == 'meta'}
        image_url = urlsplit(meta['og:image'])
        self.assertEqual(image_url.scheme, 'https')
        self.assertEqual(image_url.netloc, 'sungryulcho.github.io')
        self.assertEqual(image_url.path, '/images/portfolio-share-crop-20260930.png')
        self.assertEqual(meta['twitter:image'], meta['og:image'])
        self.assertEqual(meta['twitter:card'], 'summary_large_image')
        self.assertEqual(meta['twitter:title'], meta['og:title'])
        self.assertEqual(meta['twitter:description'], meta['og:description'])
        self.assertEqual(meta['og:title'], 'Portfolio')
        self.assertEqual(meta['og:description'], '')
        self.assertEqual(meta['twitter:image:alt'], meta['og:image:alt'])
        self.assertIn('Sung Ryul Cho', meta['og:image:alt'])
        self.assertNotIn('Backend', meta['og:image:alt'])
        image = (ROOT / image_url.path.lstrip('/')).read_bytes()
        self.assertEqual(image[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual(image[12:16], b'IHDR')
        width = int.from_bytes(image[16:20], 'big')
        height = int.from_bytes(image[20:24], 'big')
        self.assertEqual((int(meta['og:image:width']), int(meta['og:image:height'])),
                         (width, height))
        self.assertEqual(meta['og:image:type'], 'image/png')
        self.assertGreaterEqual(width, 1200)
        self.assertEqual((width, height), (1572, 786))
        self.assertEqual(width / height, 2)
        self.assertLess(len(image), 2 * 1024 * 1024)

    def test_share_banner_does_not_replace_the_site_portrait(self):
        portraits = [attrs for tag, attrs in self.nodes
                     if tag == 'img' and attrs.get('class') == 'home__avatar']
        self.assertEqual(len(portraits), 1)
        self.assertEqual(portraits[0]['src'], 'images/profile.png')

    def test_project_galleries_keep_existing_and_added_images(self):
        expected = {
            'dekk': [('카드 탐색', 'dekk-main.png'), ('덱 목록', 'dekk-decks.png'), ('링크 공유', 'dekk-share.png')],
            'learnflow': [('메인', 'learnflow-home.png'), ('AI 요약', 'learnflow-ai-summary.png'), ('리뷰', 'learnflow-reviews.png')],
            'vench': [('생성 중', 'vench-progress.png'), ('생성 결과', 'vench-result.png'), ('지난 기록', 'vench-history-demo.png')],
        }
        for project_id, screens in expected.items():
            project = self.html.split('<li id="project-' + project_id + '"', 1)[1].split('<div class="project__metadata">', 1)[0]
            parser = SiteParser()
            parser.feed(project)
            slides = [attrs for tag, attrs in parser.nodes
                      if tag == 'a' and attrs.get('class') == 'project__gallery-slide']
            self.assertEqual([(slide['data-image-label'], Path(slide['href']).name) for slide in slides], screens)
            for slide in slides:
                self.assertTrue((ROOT / slide['href']).is_file())
                self.assertNotIn('hidden', slide)
                self.assertEqual(slide['target'], '_blank')
                self.assertIn('새 탭', slide['aria-label'])
            self.assertNotIn('project__gallery-controls', project)
            self.assertNotIn('project__gallery-caption', project)
            self.assertNotIn('data-gallery-prev', project)
            self.assertNotIn('data-gallery-next', project)
            self.assertNotIn('aria-live="polite"', project)
        learnflow = self.html.split('<li id="project-learnflow"', 1)[1].split('<div class="project__metadata">', 1)[0]
        self.assertNotIn('예시 데이터', learnflow)
        self.assertNotIn('images/projects/vench-history.jpg', self.html)
        self.assertIn('<script src="src/project-gallery.js?v=20260930-autoplay-3s" defer></script>', self.html)

    def test_gallery_keeps_existing_image_area_at_each_breakpoint(self):
        css = (ROOT / 'css/style.css').read_text()
        base = css.split('\n.project__gallery {', 1)[1].split('}', 1)[0]
        self.assertIn('height: 210px;', base)
        tablet = css.split('@media (max-width: 1100px) and (min-width: 769px)', 1)[1].split('@media (max-width: 768px)', 1)[0]
        mobile = css.split('@media (max-width: 768px)', 1)[1].split('@media (max-width: 400px)', 1)[0]
        for block, height in ((tablet, 170), (mobile, 240)):
            self.assertIn('.project__img { height: ' + str(height) + 'px; }', block)
            self.assertIn('.project__gallery { height: ' + str(height) + 'px; }', block)
        self.assertIn('.project__gallery .project__img { height: 100%; padding: .25rem; }', css)
        self.assertNotIn('height: calc(100% - 36px);', css)
        self.assertNotIn('.project__gallery-caption', css)
        self.assertIn('scroll-snap-type: x mandatory;', css)

    def test_resume_statuses_are_explicit(self):
        for value in ('컴퓨터공학과 · 졸업', '정보처리기사 필기 합격', '실기 준비 중', '수강 중', '960시간', '420시간', '2026.08.28'):
            self.assertIn(value, self.html)
        self.assertNotIn('졸업 예정', self.html)

    def test_user_corrected_grade(self):
        self.assertIn('평점 3.94 / 4.5', self.html)
        self.assertNotIn('3.93', self.html)

    def test_user_confirmed_education_and_award_dates(self):
        about = self.html.split('<section id="about"', 1)[1].split('</section>', 1)[0]
        self.assertIn('2022.02 – 2026.08', about)
        self.assertNotIn('2022.03', about)
        awards = self.html.split('<section aria-labelledby="awards-title">', 1)[1].split('</section>', 1)[0]
        self.assertIn('<span class="credential__date">2026.03</span><h4>원티드랩 포텐업 Final Project 전체 1위</h4>', awards)
        self.assertNotIn('2026.04', awards)
        dekk = self.html.split('<li id="project-dekk"', 1)[1].split('<h3', 1)[0]
        self.assertIn('2026.02 – 2026.04', dekk)

    def test_requested_hero_and_no_site_implementation_sentence(self):
        self.assertIn('>Sung Ryul Cho</strong>', self.html)
        self.assertNotIn('이 사이트는 HTML', self.html)

    def test_hero_actions_share_width_and_retain_visual_hierarchy(self):
        home = self.html.split('<section id="home"', 1)[1].split('</section>', 1)[0]
        parser = SiteParser()
        parser.feed(home)
        actions = [attrs for tag, attrs in parser.nodes
                   if tag == 'a' and 'home__contact' in attrs.get('class', '').split()]
        self.assertEqual([action['href'] for action in actions], ['#work', '#contact'])
        self.assertEqual(actions[1]['class'], 'home__contact home__contact--outline')
        css = (ROOT / 'css/style.css').read_text()
        base_rule = css.split('\n.home__contact {', 1)[1].split('}', 1)[0]
        outline_rule = css.split('\n.home__contact--outline {', 1)[1].split('}', 1)[0]
        for value in ('width: 8.75rem;', 'max-width: calc(100% - .8rem);',
                      'padding: .6rem 1.1rem;', 'background: var(--color-accent);'):
            self.assertIn(value, base_rule)
        self.assertIn('background: transparent;', outline_rule)
        self.assertNotIn('width:', outline_rule)

    def test_education_course_and_org_labels_are_consistent(self):
        items = self.html.split('<article class="education-item">')[1:]
        self.assertEqual(len(items), 2)
        for item in items:
            content = item.split('</article>', 1)[0]
            self.assertEqual(content.count('<p>교육 과정:'), 1)
            self.assertEqual(content.count('<p class="education-item__org">기관:'), 1)

    def test_project_filters_share_dimensions_without_resizing_cards(self):
        filters = [attrs for tag, attrs in self.nodes
                   if tag == 'button' and 'category' in attrs.get('class', '').split()]
        self.assertEqual([item['data-category'] for item in filters], ['all', 'backend', 'ai'])
        css = (ROOT / 'css/style.css').read_text()
        group_rule = css.split('\n.categories {', 1)[1].split('}', 1)[0]
        button_rule = css.split('\n.category {', 1)[1].split('}', 1)[0]
        for value in ('flex-wrap: wrap;', 'justify-content: center;', 'gap: .625rem;'):
            self.assertIn(value, group_rule)
        for value in ('width: 10.625rem;', 'min-height: 2.75rem;',
                      'justify-content: center;', 'gap: .5rem;'):
            self.assertIn(value, button_rule)
        self.assertIn('max-width: calc((100% - .5rem) / 2);', css)
        grid_rule = css.split('\n.projects {', 1)[1].split('}', 1)[0]
        self.assertIn('grid-template-columns: repeat(3,minmax(0,1fr));', grid_rule)
        self.assertIn('gap: 1.25rem;', grid_rule)

    def test_filter_counts_keep_same_centered_badges_in_both_states(self):
        css = (ROOT / 'css/style.css').read_text()
        badge = css.split('\n.category__count {', 1)[1].split('}', 1)[0]
        for value in ('display: inline-flex;', 'align-items: center;', 'justify-content: center;',
                      'flex-shrink: 0;', 'width: 1.375rem;', 'height: 1.375rem;',
                      'font-size: .875rem;', 'font-weight: 700;', 'line-height: 1;',
                      'border-radius: 50%;', 'color: white;', 'background: #293646;'):
            self.assertIn(value, badge)
        self.assertNotIn('.category--selected .category__count', css)
        selected_button = css.split('\n.category--selected {', 1)[1].split('}', 1)[0]
        self.assertIn('background: var(--color-accent);', selected_button)

    def test_concise_sections_and_consistent_skill_cards(self):
        for subtitle in ('프로젝트에서 이렇게 사용했습니다', '교육 · 자격 · 수상',
                         '서비스의 흐름과 안정성을 고민한 세 가지 프로젝트', 'AI Pipeline'):
            self.assertNotIn(subtitle, self.html)
        cards = [attrs for _, attrs in self.nodes if 'skill-card' in attrs.get('class', '').split()]
        self.assertEqual(len(cards), 6)
        self.assertTrue(all('aria-labelledby' in attrs for attrs in cards))
        self.assertNotIn('사용 프로젝트', self.html)
        self.assertNotIn('skill-card__projects', self.html)
        for card in self.html.split('<section class="skill-card"')[1:]:
            content = card.split('</section>', 1)[0]
            self.assertEqual(content.count('class="skill-card__tools"'), 1)
            self.assertEqual(content.count('class="skill-card__usage"'), 1)

    def test_project_cases_show_problem_decision_and_improvement(self):
        self.assertNotIn('문제 해결과 검증', self.html)
        self.assertEqual(self.html.count('<summary>문제 해결과 개선</summary>'), 3)
        cases = self.html.split('<dl class="case-flow">')[1:]
        self.assertEqual(len(cases), 10)
        for case in cases:
            content = case.split('</dl>', 1)[0]
            self.assertEqual(content.count('<dt>'), 3)
            self.assertLess(content.index('<dt>문제</dt>'), content.index('<dt>해결 방안 검토</dt>'))
            self.assertLess(content.index('<dt>해결 방안 검토</dt>'), content.index('<dt>해결·개선</dt>'))

    def test_backend_project_mapping_and_clear_responsibilities(self):
        for project_id, stack in (('dekk', 'Java · Spring Boot'),
                                  ('learnflow', 'Java · Spring Boot'),
                                  ('vench', 'Python · FastAPI')):
            project = self.html.split('<li id="project-' + project_id + '"', 1)[1]
            project_stack = project.split('<p class="project__stack">', 1)[1].split('</p>', 1)[0]
            self.assertIn(stack, project_stack)
        for count, tasks in zip((6, 4, 4), self.html.split('<ul class="project__tasks">')[1:]):
            items = tasks.split('</ul>', 1)[0].split('<li>')[1:]
            self.assertEqual(len(items), count)
            for item in items:
                text = item.split('</li>', 1)[0]
                self.assertTrue(text.endswith(('구현', '구성', '개선', '해결')), text)

    def test_responsibilities_explain_features_before_technical_details(self):
        self.assertIn('패션 카드를 컬렉션(덱)에 모으고', self.html)
        for count, tasks in zip((6, 4, 4), self.html.split('<ul class="project__tasks">')[1:]):
            content = tasks.split('</ul>', 1)[0]
            self.assertEqual(content.count('<strong>'), count)
            self.assertEqual(content.count(':</strong>'), count)
            for implementation_term in ('Outbox', '작업 선점', '분산 락', '메트릭', '토큰 재발급'):
                self.assertNotIn(implementation_term, content)
        for retained_detail in ('Redisson 분산 락', 'Outbox', 'GROUP BY와 ROW_NUMBER', 'BackgroundTasks'):
            self.assertIn(retained_detail, self.html)

    def test_query_improvement_scope_and_ai_retry_outcome_are_explicit(self):
        dekk = self.html.split('id="dekk-query-improvement"', 1)[1].split('</article>', 1)[0]
        for fact in ('두 종류의 보조 쿼리를 N + N회에서 1 + 1회로',
                     '이 두 조회의 실행 횟수는 증가하지 않도록'):
            self.assertIn(fact, dekk)
        learnflow = self.html.split('id="learnflow-ai-outbox"', 1)[1].split('</article>', 1)[0]
        for fact in ('강의 승인과 AI 분석 작업의 분리 및 실패 재처리',
                     '하나의 트랜잭션', '대기, 처리 중, 완료, 실패',
                     '다음 실행 시각', '1분, 5분, 60분 간격으로 최대 3회',
                     '한도를 넘으면 실패 상태로', '승인 요청과 시간이 오래 걸리는 분석 실행을 분리'):
            self.assertIn(fact, learnflow)

    def test_responsibilities_share_dialog_and_keep_native_fallback(self):
        triggers = [attrs for tag, attrs in self.nodes
                    if tag == 'button' and attrs.get('class') == 'project__tasks-trigger']
        self.assertEqual([attrs['id'] for attrs in triggers],
                         ['dekk-tasks-open', 'learnflow-tasks-open', 'vench-tasks-open'])
        for trigger in triggers:
            self.assertEqual(trigger['aria-haspopup'], 'dialog')
            self.assertEqual(trigger['aria-controls'], 'project-case-dialog')
            self.assertIn('담당한 일 보기', trigger['aria-label'])
            self.assertIn('hidden', trigger)
        disclosures = [attrs for tag, attrs in self.nodes
                       if tag == 'details' and attrs.get('class') == 'project__responsibilities']
        self.assertEqual(len(disclosures), 3)
        self.assertTrue(all('open' not in attrs for attrs in disclosures))
        for name, count, project in zip(('DEKK', 'LearnFlow', 'Vench AI'), (6, 4, 4),
                                        self.html.split('<li id="project-')[1:]):
            before, after = project.split('</details>', 1)
            self.assertIn('<summary aria-label="' + name + ' 담당한 일">', before)
            self.assertIn('<ul class="project__tasks">', before)
            self.assertIn('project__tasks-trigger', before.split('<details class="project__responsibilities">', 1)[0])
            self.assertEqual(before.count('<li>'), count)
            self.assertNotIn('project__detail-trigger', before)
            self.assertIn('project__detail-trigger', after.split('<details class="project__detail">', 1)[0])
        css = (ROOT / 'css/style.css').read_text()
        self.assertIn('.project__responsibilities[open] .project__responsibilities-icon', css)
        self.assertIn('.project__responsibilities summary:focus-visible', css)
        self.assertIn('.case-dialog .project__tasks', css)
        script = (ROOT / 'src/project-dialog.js').read_text()
        self.assertIn("title: '담당한 일'", script)
        self.assertIn('title.textContent = entry.title', script)
        self.assertIn('body.tabIndex = 0', script)

    def test_all_dialog_views_fit_content_with_viewport_cap(self):
        css = (ROOT / 'css/style.css').read_text()
        dialog_rule = css.split('\n.case-dialog {', 1)[1].split('}', 1)[0]
        self.assertIn('height: fit-content;', dialog_rule)
        self.assertIn('max-height: min(740px, calc(100dvh - 3rem));', dialog_rule)
        self.assertIn('.case-dialog { width: 100%; max-height: 100dvh;', css)
        self.assertNotRegex(css, r'(?<![-\w])height:\s*100dvh;')

    def test_member_takeover_and_deployment_roles_are_explicit(self):
        dekk = self.html.split('<li id="project-dekk"', 1)[1].split('<li id="project-learnflow"', 1)[0]
        for fact in ('회원 관리 인수:', '공통 인증 정책의 수정 지점',
                     '같은 트랜잭션에서 실행되는 이벤트 핸들러',
                     '인프라 전체 구조 설계는 팀원이 맡고',
                     'codedeploy-agent가 중지된 것을 확인하고 기동',
                     '재배포가 정상 완료'):
            self.assertIn(fact, dekk)
        for unsupported_claim in ('비동기 이벤트', '전체 인프라를 설계', '응답 속도 향상'):
            self.assertNotIn(unsupported_claim, dekk)

    def test_each_case_links_to_specific_public_evidence(self):
        cases = self.html.split('<article class="project__case"')[1:]
        self.assertEqual(len(cases), 10)
        for case in cases:
            content = case.split('</article>', 1)[0]
            parser = SiteParser()
            parser.feed(content)
            evidence = [attrs for tag, attrs in parser.nodes if tag == 'a']
            self.assertGreaterEqual(len(evidence), 1)
            for attrs in evidence:
                url = urlsplit(attrs['href'])
                self.assertEqual(url.scheme, 'https')
                self.assertEqual(url.netloc, 'github.com')
                self.assertRegex(url.path, r'^/[^/]+/[^/]+/(pull/\d+|blob/[a-f0-9]{40}/.+|commit/[a-f0-9]{40})$')
        self.assertIn('중복 저장 동시성 테스트', self.html)
        self.assertIn('팀 배포 구성 코드', self.html)

    def test_all_projects_use_shared_dialog_with_inline_fallback(self):
        dialogs = [attrs for tag, attrs in self.nodes if tag == 'dialog']
        self.assertEqual(len(dialogs), 1)
        self.assertEqual(dialogs[0]['id'], 'project-case-dialog')
        ids = {attrs['id'] for _, attrs in self.nodes if 'id' in attrs}
        for label_id in dialogs[0]['aria-labelledby'].split():
            self.assertIn(label_id, ids)
        triggers = [attrs for tag, attrs in self.nodes
                    if attrs.get('class') == 'project__detail-trigger']
        self.assertEqual([attrs['id'] for attrs in triggers],
                         ['dekk-details-open', 'learnflow-details-open', 'vench-details-open'])
        for trigger in triggers:
            self.assertEqual(trigger['aria-haspopup'], 'dialog')
            self.assertEqual(trigger['aria-controls'], dialogs[0]['id'])
            self.assertIn('hidden', trigger)
            self.assertIn('문제 해결과 개선 보기', trigger['aria-label'])
        cases = [attrs for tag, attrs in self.nodes if 'data-case-label' in attrs]
        self.assertEqual([attrs['data-case-label'] for attrs in cases],
                         ['회원 관리 개선', '동시 저장', '조회 개선', '배포 협업',
                          'AI 작업 연결', '리뷰 조회', '배포 개선',
                          '진행 및 실패 대응', '음성 입력', '감정 통계'])
        self.assertTrue(all(attrs.get('id') in ids for attrs in cases))
        # Original details and source content remain present if enhancement fails to load.
        self.assertEqual(self.html.count('<details class="project__detail">'), 3)
        self.assertIn('<script src="src/project-dialog.js?v=20260930-compact-cases" defer></script>', self.html)

    def test_expanded_project_cases_have_distinct_topics_and_boundaries(self):
        learnflow = self.html.split('<li id="project-learnflow"', 1)[1].split('<li id="project-vench"', 1)[0]
        vench = self.html.split('<li id="project-vench"', 1)[1].split('<details class="project__detail">', 1)[1].split('</details>', 1)[0]
        for project in (learnflow, vench):
            self.assertEqual(project.count('<article class="project__case"'), 3)
        for case_id in ('learnflow-review-query', 'learnflow-deployment-improvement',
                        'vench-audio-input', 'vench-emotion-report'):
            self.assertIn('id="' + case_id + '"', self.html)
        self.assertIn('후속 heartbeat·workerId 고도화는 팀 구현', learnflow)
        self.assertIn('최신 3개만', learnflow)
        audio = vench.split('id="vench-audio-input"', 1)[1].split('</article>', 1)[0]
        self.assertIn('음량 정규화를 추가하고', audio)
        self.assertNotIn('정확도 향상', audio)
        self.assertNotIn('%', audio)
        progress = vench.split('id="vench-ai-progress"', 1)[1].split('</article>', 1)[0]
        self.assertIn('프로세스 재시작 후 자동 복구까지 보장하는 구조는 아닙니다', progress)
        css = (ROOT / 'css/style.css').read_text()
        self.assertIn('repeat(var(--case-count, 4), minmax(0, 1fr))', css)

    def test_repository_links_are_secondary_inside_details(self):
        self.assertNotIn('GitHub에서 코드 보기', self.html)
        for project in self.html.split('<li id="project-')[1:]:
            metadata = project.split('<details class="project__detail">', 1)[1].split('</details>', 1)
            detail = metadata[0]
            self.assertEqual(detail.count('class="project__link"'), 1)
            self.assertIn('전체 GitHub 저장소 ↗', detail)
            self.assertNotIn('class="project__link"', metadata[1].split('</div>', 1)[0])
        css = (ROOT / 'css/style.css').read_text()
        trigger_rule = css.split('\n.project__detail-trigger {', 1)[1].split('}', 1)[0]
        self.assertIn('justify-content: flex-start', trigger_rule)
        self.assertIn('gap: .35rem', trigger_rule)

    def test_repository_links_move_to_project_header_for_case_views(self):
        self.assertIn('<div class="case-dialog__meta"><p id="case-dialog-project"', self.html)
        self.assertIn('<h2 id="case-dialog-title" class="case-dialog__title">', self.html)
        script = (ROOT / 'src/project-dialog.js').read_text()
        self.assertIn("repository: body.querySelector('.project__link')", script)
        self.assertIn('projectMeta.append(entry.repository)', script)
        self.assertIn("entry.repository.textContent = 'GitHub ↗'", script)
        self.assertIn('if (item.repository) item.repository.hidden = item !== entry', script)
        css = (ROOT / 'css/style.css').read_text()
        self.assertIn('.case-dialog__meta { display: flex; flex-wrap: wrap;', css)
        self.assertIn('.case-dialog .case-dialog__repository', css)
        self.assertNotIn('.case-dialog .project__link {', css)
        link_rule = css.split('.case-dialog .case-dialog__repository {', 1)[1].split('}', 1)[0]
        for affordance in ('min-height: 24px;', 'border: 1px solid', 'background: transparent;', 'font-size: .75rem;', 'font-weight: 500;'):
            self.assertIn(affordance, link_rule)
        project_rule = css.split('.case-dialog__project {', 1)[1].split('}', 1)[0]
        self.assertIn('font-size: 1.25rem;', project_rule)
        self.assertIn('font-weight: 700;', project_rule)
        title_rule = css.split('.case-dialog__title {', 1)[1].split('}', 1)[0]
        self.assertIn('font-size: 1.5rem;', title_rule)
        self.assertIn('font-weight: 700;', title_rule)

    def test_model_names_not_listed_as_technology_stacks(self):
        for marker in ('<p class="skill-card__tools">', '<p class="project__stack">'):
            for block in self.html.split(marker)[1:]:
                stack = block.split('</p>', 1)[0]
                self.assertNotIn('EXAONE', stack)
                self.assertNotIn('mDeBERTa', stack)
        self.assertIn('Faster-Whisper · Transformers · llama.cpp', self.html)

    def test_about_summarizes_fields_and_skills_explains_capabilities(self):
        about = self.html.split('<section id="about"', 1)[1].split('</section>', 1)[0]
        self.assertEqual(about.count('<li class="major">'), 3)
        for icon in ('API', 'DB', 'OPS'):
            self.assertIn(f'aria-hidden="true">{icon}</span>', about)
        for field in ('웹 서비스 기능과<br />API 개발', '데이터 설계와<br />안정적인 처리',
                      '배포 자동화와<br />운영 환경 구성'):
            self.assertIn(field, about)
        for technology in ('Spring Boot', 'PostgreSQL', 'Redisson', 'Docker Compose'):
            self.assertNotIn(technology, about)
        self.assertIn('맡은 일을 끝까지 책임지고', about)
        skills = self.html.split('<section id="skills"', 1)[1].split('<section id="work"', 1)[0]
        for project_name in ('DEKK', 'LearnFlow', 'Vench AI'):
            self.assertNotIn(project_name, skills)
        for usage in skills.split('<p class="skill-card__usage">')[1:]:
            self.assertIn('수 있습니다.', usage.split('</p>', 1)[0])

    def test_coupang_is_described_as_operations_not_development(self):
        about = self.html.split('<section id="about"', 1)[1].split('</section>', 1)[0]
        coupang = about.split('images/jobs/coupang.png', 1)[1].split('</li>', 1)[0]
        for fact in ('쿠팡 COE Team · 상품 데이터 운영', '2024.01 – 2024.12',
                     '데이터 운영 경력', '상품 데이터 검수', '운영 보고서 작성', '유관부서와의 데이터 변경 협의 및 오류 해결'):
            self.assertIn(fact, coupang)
        for old_copy in ('Grocery Category Owner', '주 3회', '백엔드 개발로 이어가고'):
            self.assertNotIn(old_copy, coupang)

    def test_contact_has_centered_email_and_accessible_copy_icon(self):
        self.assertIn('class="contact__email-row"', self.html)
        buttons = [attrs for tag, attrs in self.nodes
                   if tag == 'button' and attrs.get('class') == 'copy-email']
        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0].get('aria-label'), '이메일 주소 복사')
        self.assertEqual(buttons[0].get('title'), '이메일 주소 복사')
        button_content = self.html.split('<button class="copy-email"', 1)[1].split('</button>', 1)[0]
        self.assertIn('<svg', button_content)
        self.assertIn('width="14" height="14"', button_content)
        self.assertIn('aria-hidden="true"', button_content)
        self.assertNotIn('>이메일 복사<', button_content)

    def test_no_proficiency_bars_or_file_module_dependency(self):
        self.assertNotIn('bar__value', self.html)
        scripts = [attrs for tag, attrs in self.nodes if tag == 'script']
        self.assertTrue(all('defer' in attrs and attrs.get('type') != 'module' for attrs in scripts))
        self.assertTrue(all(not urlsplit(attrs['src']).scheme for attrs in scripts))

    def test_only_narrow_navigation_is_vertical(self):
        css = (ROOT / 'css/style.css').read_text()
        desktop, mobile = css.split('@media (max-width: 768px)', 1)
        desktop_menu = desktop.split('.header__menu {', 1)[1].split('}', 1)[0]
        mobile_menu = mobile.split('.header__menu {', 1)[1].split('}', 1)[0]
        self.assertIn('display: flex', desktop_menu)
        self.assertNotIn('flex-direction: column', desktop_menu)
        self.assertIn('flex-direction: column', mobile_menu)
        self.assertIn('flex-wrap: nowrap', mobile_menu)
        self.assertIn('.header--enhanced .header__menu { display: none; }', mobile)
        self.assertIn('.header--enhanced .header__menu.open { display: flex;', mobile)

    def test_images_and_external_links_accessible(self):
        for tag, attrs in self.nodes:
            if tag == 'img':
                self.assertIn('alt', attrs)
                self.assertIn('width', attrs)
                self.assertIn('height', attrs)
            if tag == 'a' and attrs.get('target') == '_blank':
                self.assertIn('noopener', attrs.get('rel', ''))
                self.assertIn('새 탭', attrs.get('aria-label', ''))

if __name__ == '__main__':
    unittest.main(verbosity=2)
