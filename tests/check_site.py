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

    def test_card_headings_are_distinct_from_body_without_affecting_cases(self):
        css = (ROOT / 'css/style.css').read_text()
        heading = css.split('\n.project__role-summary h4 {', 1)[1].split('}', 1)[0]
        body = css.split('\n.project__role-summary li {', 1)[1].split('}', 1)[0]
        for value in ('font-size: 1.125rem;', 'font-weight: 700;',
                      'color: #abc9f0;', 'margin-bottom: .625rem;'):
            self.assertIn(value, heading)
        self.assertIn('font-size: .95rem;', body)
        self.assertIn('line-height: 1.75;', body)
        stack = css.split('\n.project__stack {', 1)[1].split('}', 1)[0]
        self.assertNotIn('min-height:', stack)
        self.assertNotIn('project__outcome-summary', css)
        trigger = css.split('\n.project__detail-trigger {', 1)[1].split('}', 1)[0]
        fallback = css.split('\n.project__detail summary {', 1)[1].split('}', 1)[0]
        for rule in (trigger, fallback):
            self.assertIn('font-size: 1.125rem;', rule)
            self.assertIn('font-weight: 700;', rule)

    def test_project_cards_use_three_two_and_one_columns(self):
        css = (ROOT / 'css/style.css').read_text()
        desktop = css.split('\n.projects {', 1)[1].split('}', 1)[0]
        tablet = css.split('@media (max-width: 1199px) {', 1)[1].split('@media', 1)[0]
        mobile = css.split('@media (max-width: 768px) {', 1)[1].split('@media', 1)[0]
        self.assertIn('grid-template-columns: repeat(3,minmax(0,1fr));', desktop)
        self.assertIn('grid-template-columns: repeat(2, minmax(0, 1fr));', tablet)
        self.assertIn('.projects { grid-template-columns: 1fr;', mobile)
        self.assertNotIn('min-height: 6.8em;', css)

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

    def test_project_cases_show_problem_decision_improvement_and_outcome(self):
        self.assertNotIn('문제 해결과 검증', self.html)
        self.assertEqual(self.html.count('<summary>문제 해결과 성과 보기</summary>'), 3)
        cases = self.html.split('<dl class="case-flow">')[1:]
        self.assertEqual(len(cases), 11)
        for case in cases:
            content = case.split('</dl>', 1)[0]
            self.assertEqual(content.count('<dt>'), 4)
            self.assertLess(content.index('<dt>문제</dt>'), content.index('<dt>해결 방안 검토</dt>'))
            self.assertLess(content.index('<dt>해결 방안 검토</dt>'), content.index('<dt>해결·개선</dt>'))
            self.assertLess(content.index('<dt>해결·개선</dt>'), content.index('<dt>성과</dt>'))
            self.assertEqual(content.count('class="case-flow__outcome"'), 1)
            outcome = content.split('<dt>성과</dt><dd>', 1)[1].split('</dd>', 1)[0]
            self.assertLessEqual(len(outcome), 90)
            self.assertEqual(outcome.count('.'), 1)
            self.assertNotIn('<br', outcome)
            self.assertNotIn('<a ', outcome)
            self.assertLess(case.index('<dt>성과</dt>'), case.index('class="project__evidence"'))

    def test_outcomes_keep_existing_layout_and_receive_only_text_emphasis(self):
        css = (ROOT / 'css/style.css').read_text()
        rule = css.split('.case-flow .case-flow__outcome dd {', 1)[1].split('}', 1)[0]
        self.assertIn('font-weight: 700;', rule)
        self.assertNotIn('background', rule)
        self.assertNotIn('height', rule)

    def test_backend_project_mapping_and_clear_responsibilities(self):
        for project_id, stack in (('dekk', 'Java · Spring Boot'),
                                  ('learnflow', 'Java · Spring Boot'),
                                  ('vench', 'Python · FastAPI')):
            project = self.html.split('<li id="project-' + project_id + '"', 1)[1]
            project_stack = project.split('<p class="project__stack">', 1)[1].split('</p>', 1)[0]
            self.assertIn(stack, project_stack)
        roles = self.html.split('<div class="project__role-summary">')[1:]
        self.assertEqual(len(roles), 3)
        for role in roles:
            content = role.split('</div>', 1)[0]
            self.assertEqual(content.count('<ul>'), 1)
            self.assertEqual(content.count('<li>'), 3)
            self.assertNotIn('<p>', content)
            for item in content.split('<li>')[1:]:
                self.assertLessEqual(len(item.split('</li>', 1)[0]), 40)
        css = (ROOT / 'css/style.css').read_text()
        list_rule = css.split('\n.project__role-summary ul {', 1)[1].split('}', 1)[0]
        self.assertIn('list-style: disc;', list_rule)
        self.assertIn('padding-left: 1.2em;', list_rule)

    def test_responsibilities_explain_features_before_technical_details(self):
        self.assertIn('패션 카드를 보관함에 모으고', self.html)
        for role in self.html.split('<div class="project__role-summary">')[1:]:
            content = role.split('</div>', 1)[0]
            self.assertNotIn('<strong>', content)
            for implementation_term in ('Outbox', '작업 선점', '분산 락', '메트릭', '토큰 재발급'):
                self.assertNotIn(implementation_term, content)
        for service_context in ('개인/공유 보관함과 링크 공유 기능 개발',
                                '강의 승인부터 AI 요약 제공까지 서버 처리 구현',
                                '음성 인식, 감정 분석, 일기 생성 흐름 연동'):
            self.assertIn(service_context, self.html)
        for retained_detail in ('Redisson 분산 락', 'Outbox', 'ROW_NUMBER', 'BackgroundTasks'):
            self.assertIn(retained_detail, self.html)

    def test_dekk_card_connects_service_and_ownership_to_case_entry(self):
        project = self.html.split('<li id="project-dekk"', 1)[1].split('</li>\n          <li id="project-learnflow"', 1)[0]
        card, details = project.split('<details class="project__detail">', 1)
        role = card.split('<div class="project__role-summary">', 1)[1].split('</div>', 1)[0]
        self.assertIn('개인/공유 보관함과 링크 공유 기능 개발', role)
        self.assertIn('회원 관리 기능 인수 및 인증 구조 개선', role)
        self.assertIn('관리자 기능 개발 및 서버 배포', role)
        self.assertLess(card.index('project__intro'), card.index('project__role-summary'))
        self.assertLess(card.index('project__role-summary'), card.index('project__detail-trigger'))
        self.assertNotIn('project__outcome-summary', card)
        self.assertNotIn('project__outcome-summary', details)
        self.assertIn('인증 정책의 일관성과 유지보수성을 높였습니다', details)
        for case in ('dekk-member-improvement', 'dekk-member-deck-separation', 'dekk-concurrent-save',
                     'dekk-query-improvement', 'dekk-deployment-collaboration'):
            self.assertIn('id="' + case + '"', details)

    def test_learnflow_card_keeps_ownership_and_outcomes_in_details(self):
        project = self.html.split('<li id="project-learnflow"', 1)[1].split('<li id="project-vench"', 1)[0]
        card, details = project.split('<details class="project__detail">', 1)
        role = card.split('<div class="project__role-summary">', 1)[1].split('</div>', 1)[0]
        self.assertIn('AI 요약으로 강의 내용을 미리 확인', card)
        self.assertNotIn('AI 요약으로 복습', card)
        self.assertIn('강의 승인부터 AI 요약 제공까지 서버 처리 구현', role)
        self.assertIn('수강생 리뷰와 강사 답글 기능', role)
        self.assertIn('서버 배포 및 오류 추적 환경', role)
        self.assertLess(card.index('project__intro'), card.index('project__role-summary'))
        self.assertLess(card.index('project__role-summary'), card.index('project__detail-trigger'))
        self.assertNotIn('project__outcome-summary', card)
        self.assertNotIn('project__outcome-summary', details)
        self.assertIn('관리자의 승인 대기 부담을 줄이고', details)
        self.assertNotIn('ML 워커와 화면, 후속 heartbeat·workerId 고도화는 팀 구현입니다.', details)
        for case in ('learnflow-ai-outbox', 'learnflow-review-query',
                     'learnflow-deployment-improvement'):
            self.assertIn('id="' + case + '"', details)

    def test_vench_card_keeps_ai_ownership_and_progress_outcome_in_details(self):
        project = self.html.split('<li id="project-vench"', 1)[1].split('<section id="education"', 1)[0]
        card, details = project.split('<details class="project__detail">', 1)
        role = card.split('<div class="project__role-summary">', 1)[1].split('</div>', 1)[0]
        self.assertIn('지난 기록과 감정 통계를 확인', card)
        self.assertIn('음성 인식, 감정 분석, 일기 생성 흐름 연동', role)
        self.assertIn('일기 기록과 누적 감정 통계 조회 API', role)
        self.assertIn('AI 처리 진행 상태', role)
        self.assertIn('이용 현황', role)
        self.assertLess(card.index('project__intro'), card.index('project__role-summary'))
        self.assertLess(card.index('project__role-summary'), card.index('project__detail-trigger'))
        self.assertNotIn('project__outcome-summary', card)
        self.assertNotIn('project__outcome-summary', details)
        self.assertIn('처리 단계 안내로 사용자의 진행 상황 파악을 돕고', details)
        self.assertNotIn('프로세스 재시작 후 자동 복구까지 보장하는 구조는 아닙니다.', details)
        for case in ('vench-ai-progress', 'vench-audio-input', 'vench-emotion-report'):
            self.assertIn('id="' + case + '"', details)

    def test_query_improvement_scope_and_ai_retry_outcome_are_explicit(self):
        dekk = self.html.split('id="dekk-query-improvement"', 1)[1].split('</article>', 1)[0]
        for fact in ('전체 카드를 가져온 뒤 애플리케이션에서 정렬하고 3장을',
                     '보관함별 최신 카드 3장만 조회',
                     '전체 카드 수도 표시해야 하므로 기존 집계는 유지',
                     '보관함 목록 조회의 처리 효율을 높였습니다',
                     'commit/2df04598d52b99e48f09742588ba99b82aa1227a',
                     'commit/79f83a38e8c9b143876046e1edc87b451f7c6dc6'):
            self.assertIn(fact, dekk)
        for unsupported_comparison in ('N + N', '1 + 1', '응답 속도가', 'ms로'):
            self.assertNotIn(unsupported_comparison, dekk)
        learnflow = self.html.split('id="learnflow-ai-outbox"', 1)[1].split('</article>', 1)[0]
        for fact in ('강의 승인을 기다리게 하지 않는 AI 요약 작업 처리',
                     '하나의 트랜잭션', '대기, 처리 중, 완료, 실패',
                     '분석 서버가 실패를 알린 작업', '1분, 5분, 60분 뒤에',
                     '최대 3회의 재시도', 'AI 분석과 승인을 분리해 관리자의 승인 대기 부담을 줄이고',
                     '승인과 분석 작업을 함께 저장해 작업 연결의 안정성을 높였습니다'):
            self.assertIn(fact, learnflow)

    def test_learnflow_team_note_is_removed_without_expanding_claims(self):
        note = 'ML 워커와 화면, 후속 heartbeat·workerId 고도화는 팀 구현입니다.'
        ai_case = self.html.split('id="learnflow-ai-outbox"', 1)[1].split('</article>', 1)[0]
        self.assertNotIn(note, self.html)
        self.assertNotIn('project__note', ai_case)
        self.assertIn('분석 서버가 작업을 가져가 결과를 전달하는 API를 구현했습니다.', ai_case)
        self.assertNotIn('ML 워커를 구현', ai_case)
        self.assertNotIn('제 기여는 초기 Outbox·리뷰·배포 및 추적입니다.', self.html)
        for case_id in ('learnflow-review-query', 'learnflow-deployment-improvement'):
            case = self.html.split('id="' + case_id + '"', 1)[1].split('</article>', 1)[0]
            self.assertNotIn('project__note', case)
            self.assertNotIn(note, case)

    def test_learnflow_cases_keep_implementation_facts_and_evidence(self):
        cases = {
            'learnflow-ai-outbox': ('강의 승인을 기다리게 하지 않는 AI 요약 작업 처리',
                                   '관리자가 분석 완료까지 기다리는 상황',
                                   '승인된 강의의 분석 작업이 누락되는 상황을 피해야',
                                   '승인 정보와 작업 기록은 같은 트랜잭션으로 저장',
                                   'pull/117'),
            'learnflow-review-query': ('리뷰마다 반복하던 작성자 정보 조회 개선',
                                      '리뷰마다 회원 정보를 따로 조회',
                                      '작성자 ID를 모아 한꺼번에 조회하는 방식을 선택',
                                      '기존 페이지 처리를 바꾸지 않고도 같은 작성자의 정보를 여러 리뷰에서 재사용',
                                      'pull/28'),
            'learnflow-deployment-improvement': ('배포 스크립트의 중복 실행 제거와 백업 관리',
                                                '실행을 중복으로 시도',
                                                '백업은 최신 3개만 남기도록',
                                                'pull/127'),
        }
        for case_id, facts in cases.items():
            with self.subTest(case=case_id):
                case = self.html.split('id="' + case_id + '"', 1)[1].split('</article>', 1)[0]
                for fact in facts:
                    self.assertIn(fact, case)
                for label in ('문제', '해결 방안 검토', '해결·개선', '성과'):
                    self.assertEqual(case.count('<dt>' + label + '</dt>'), 1)
                self.assertEqual(case.count('class="project__evidence"'), 1)

    def test_vench_cases_keep_implementation_facts_and_evidence(self):
        cases = {
            'vench-ai-progress': ('AI 처리 단계 안내와 생성 실패 시 대체 결과 제공',
                                  'HTTP 202 응답과 일기 ID를 먼저 반환',
                                  '진행 안내를 DB에 기록',
                                  '일기 본문 생성 중 예외가 발생하면',
                                  'diary_task.py', 'diary_generation_service.py'),
            'vench-audio-input': ('음성 인식 오류에 대응한 전처리·모델 설정 변경',
                                  '기존 16kHz 모노 WAV 변환 과정에 음량 정규화를 추가',
                                  'small에서 medium으로 변경',
                                  'commit/d964e6577fe6ed542e3f490bc778b2c9c519c4f6'),
            'vench-emotion-report': ('대표 감정 하나만 집계하던 통계 개선',
                                     '저장된 다른 감정 점수가 빠져',
                                     '동일한 점수 누적 방식으로 맞췄습니다',
                                     'commit/6cb45241a7a45993ec733d6380daf4d2ad985330'),
        }
        for case_id, facts in cases.items():
            with self.subTest(case=case_id):
                case = self.html.split('id="' + case_id + '"', 1)[1].split('</article>', 1)[0]
                for fact in facts:
                    self.assertIn(fact, case)
                for label in ('문제', '해결 방안 검토', '해결·개선', '성과'):
                    self.assertEqual(case.count('<dt>' + label + '</dt>'), 1)
                self.assertEqual(case.count('class="project__evidence"'), 1)

    def test_problems_describe_effects_without_inventing_measurements(self):
        member = self.html.split('id="dekk-member-improvement"', 1)[1].split('</article>', 1)[0]
        self.assertIn('한쪽을 빠뜨리면 서로 다른 정책이 적용될 위험', member)
        separation = self.html.split('id="dekk-member-deck-separation"', 1)[1].split('</article>', 1)[0]
        self.assertIn('보관함 처리 방식이 바뀌면 회원 코드도 함께 검토', separation)
        audio = self.html.split('id="vench-audio-input"', 1)[1].split('</article>', 1)[0]
        self.assertIn('말한 내용이 텍스트로 정확하게 변환되지 않았습니다', audio)
        self.assertIn('음성 인식 전에 녹음 파일의 음량 편차를 줄였습니다', audio)
        self.assertNotIn('확인된 변경은', audio)
        self.assertNotIn('전후 비교로 확인이 필요합니다', audio)
        for unmeasured in ('정확도 향상', '정확도가 높아', '인식 오류를 해결', '%'):
            self.assertNotIn(unmeasured, audio)

    def test_role_context_stays_on_cards_and_cases_have_one_entry(self):
        triggers = [attrs for tag, attrs in self.nodes
                    if tag == 'button' and attrs.get('class') == 'project__tasks-trigger']
        self.assertEqual(triggers, [])
        summaries = [attrs for tag, attrs in self.nodes
                     if attrs.get('class') == 'project__role-summary']
        self.assertEqual(len(summaries), 3)
        self.assertTrue(all('hidden' not in attrs for attrs in summaries))
        outcomes = [attrs for tag, attrs in self.nodes
                    if attrs.get('class') == 'project__outcome-summary']
        self.assertEqual(outcomes, [])
        self.assertNotIn('대표 개선', self.html)
        self.assertEqual(self.html.count('<span>문제 해결과 성과 보기</span>'), 3)
        disclosures = [attrs for tag, attrs in self.nodes
                       if tag == 'details' and attrs.get('class') == 'project__responsibilities']
        self.assertEqual(disclosures, [])
        self.assertNotIn('담당한 일 전체 보기', self.html)
        self.assertNotIn('project__tasks', self.html)
        for project in self.html.split('<li id="project-')[1:]:
            card, details = project.split('<details class="project__detail">', 1)
            role = card.split('<div class="project__role-summary">', 1)[1].split('</div>', 1)[0]
            self.assertIn('<h4>담당 영역</h4>', role)
            self.assertEqual(role.count('<ul>'), 1)
            self.assertEqual(role.count('<li>'), 3)
            self.assertNotIn('<p>', role)
            self.assertLess(card.index('project__role-summary'), card.index('project__detail-trigger'))
            self.assertEqual(card.count('aria-haspopup="dialog"'), 1)
            self.assertNotIn('project__role-summary', details.split('</details>', 1)[0])
        css = (ROOT / 'css/style.css').read_text()
        self.assertIn('.project__role-summary li', css)
        self.assertNotIn('project__responsibilities', css)
        self.assertNotIn('project__tasks', css)
        script = (ROOT / 'src/project-dialog.js').read_text()
        self.assertIn('projectLabel.textContent = entry.name', script)
        self.assertNotIn('case-dialog-title', script)
        self.assertNotIn('responsibilities', script)
        self.assertNotIn('project__role-summary', script)
        self.assertNotIn('project__tasks-trigger', script)

    def test_all_dialog_views_fit_content_with_viewport_cap(self):
        css = (ROOT / 'css/style.css').read_text()
        dialog_rule = css.split('\n.case-dialog {', 1)[1].split('}', 1)[0]
        self.assertIn('height: fit-content;', dialog_rule)
        self.assertIn('max-height: min(740px, calc(100dvh - 3rem));', dialog_rule)
        self.assertIn('.case-dialog { width: 100%; max-height: 100dvh;', css)
        self.assertNotRegex(css, r'(?<![-\w])height:\s*100dvh;')

    def test_case_typography_preserves_title_section_body_hierarchy(self):
        css = (ROOT / 'css/style.css').read_text()
        desktop, mobile = css.split('@media (max-width: 600px)', 1)

        def rule(block, selector):
            return block.split(selector + ' {', 1)[1].split('}', 1)[0]

        def font_size(block, selector):
            return float(rule(block, selector).split('font-size:', 1)[1].split('rem', 1)[0])

        title = '.case-dialog .project__case h4'
        label = '.case-dialog .case-flow dt'
        body = '.case-dialog .case-flow dd'
        body_size = font_size(desktop, body)
        for block in (desktop, mobile):
            self.assertGreater(font_size(block, title), font_size(block, label))
            self.assertGreater(font_size(block, label), body_size)
            self.assertGreaterEqual(font_size(block, label), body_size * 1.25)
        self.assertGreaterEqual(body_size, 1)
        self.assertNotIn(body + ' {', mobile)
        self.assertIn('color: white;', rule(desktop, title))
        self.assertIn('font-weight: 700;', rule(desktop, title))
        self.assertIn('color: #d8b77c;', rule(desktop, label))
        self.assertIn('color: #d8b77c;', rule(desktop, '.case-flow dt'))
        self.assertIn('font-weight: 800;', rule(desktop, label))
        self.assertNotIn('var(--color-accent)', rule(desktop, label))
        self.assertIn('margin-bottom: .5rem;', rule(desktop, label))
        flow = rule(desktop, '.case-dialog .case-flow')
        self.assertIn('padding-left: 0;', flow)
        self.assertIn('border-left: 0;', flow)
        self.assertIn('css/style.css?v=20261008-deployment-list', self.html)

    def test_all_cases_share_approved_readability_styles(self):
        cases = [attrs for tag, attrs in self.nodes if tag == 'article'
                 and 'project__case' in attrs.get('class', '').split()]
        self.assertEqual(len(cases), 11)
        self.assertNotIn('readability-preview', self.html)
        css = (ROOT / 'css/style.css').read_text()
        self.assertNotIn('readability-preview', css)
        scope = '.case-dialog .case-flow'

        def rule(selector):
            return css.split(selector + ' {', 1)[1].split('}', 1)[0]

        title = rule('.case-dialog .project__case h4')
        self.assertIn('padding-left: 1rem;', title)
        self.assertIn('border-left: 2px solid transparent;', title)
        self.assertIn('padding-left: 0;', rule(scope))
        self.assertIn('border-left: 0;', rule(scope))
        section = rule(scope + ' > div')
        self.assertIn('padding: 1rem;', section)
        self.assertIn('border-left: 2px solid #484848;', section)
        self.assertIn('background: #ffffff06;', section)
        self.assertIn('color: #d8b77c;', rule(scope + ' dt'))
        self.assertNotIn('border-left', rule(scope + ' dd'))
        self.assertNotIn('padding-left', rule(scope + ' dd'))
        self.assertIn('margin-top: 2.25rem;', rule(scope + ' > div + div'))
        separator = rule(scope + ' > div + div::before')
        self.assertIn('content: "";', separator)
        self.assertIn('border-top: 1px solid #ffffff12;', separator)
        self.assertIn('border-left-color: #74808e;', rule(scope + ' > .case-flow__outcome'))
        self.assertNotIn(scope + ' > .case-flow__outcome dd {', css)

    def test_case_layout_keeps_compact_tabs_and_content_centered(self):
        css = (ROOT / 'css/style.css').read_text()
        desktop, mobile = css.split('@media (max-width: 600px)', 1)
        tabs = desktop.split('.case-dialog__tabs {', 1)[1].split('}', 1)[0]
        self.assertIn('grid-template-columns: repeat(var(--case-count, 4), minmax(0, 9rem));', tabs)
        self.assertIn('justify-content: center;', tabs)
        self.assertIn('padding: 0 2rem 1.25rem;', tabs)
        content = desktop.split('.case-dialog__content {', 1)[1].split('}', 1)[0]
        self.assertIn('padding: 1.75rem 2rem 2rem;', content)
        for selector in ('.case-dialog .project__cases', '.case-dialog .project__case'):
            rule = desktop.split(selector + ' {', 1)[1].split('}', 1)[0]
            self.assertIn('max-width: 840px;', rule)
            self.assertIn('margin: 0 auto;', rule)
        mobile_tabs = mobile.split('.case-dialog__tabs {', 1)[1].split('}', 1)[0]
        self.assertIn('grid-template-columns: repeat(2, minmax(0, 1fr));', mobile_tabs)

    def test_member_takeover_and_deployment_roles_are_explicit(self):
        dekk = self.html.split('<li id="project-dekk"', 1)[1].split('<li id="project-learnflow"', 1)[0]
        for fact in ('회원 관리 기능 인수 및 인증 구조 개선', '공통 인증 정책의 수정 지점',
                     '이벤트 처리는 기존 트랜잭션에 참여하도록',
                     '팀원이 설계한 인프라를 바탕으로',
                     '배포 가이드를 직접 작성해',
                     '진행 중 발생한 설정·배포 문제는 다음과 같이 해결했습니다',
                     '중지된 CodeDeploy 에이전트를 실행하고',
                     '재배포가 정상 완료되는 것을 확인했습니다'):
            self.assertIn(fact, dekk)
        for unsupported_claim in ('비동기 이벤트', '전체 인프라를 설계', '응답 속도 향상'):
            self.assertNotIn(unsupported_claim, dekk)

    def test_deployment_problem_keeps_role_context_in_action(self):
        case = self.html.split('id="dekk-deployment-collaboration"', 1)[1].split('</article>', 1)[0]
        problem = case.split('<dt>문제</dt><dd>', 1)[1].split('</dd>', 1)[0]
        action = case.split('<dt>해결·개선</dt><dd>', 1)[1].split('</dd>', 1)[0]
        self.assertEqual(problem, '배포 환경 준비가 지연되고 초기 배포가 실패하면서, 팀이 개발한 기능을 서버에 반영하지 못했습니다. 팀원들이 각자 구현한 기능을 연동하고 확인하는 작업에도 차질이 생겼습니다.')
        self.assertNotIn('팀원이 설계한', problem)
        self.assertIn('팀원이 설계한 인프라를 바탕으로', action)
        self.assertIn('동료가 이를 따라 설정 작업에 참여할 수 있도록', action)
        self.assertNotIn('예를 들어', action)
        self.assertIn('프라이빗 서브넷의 서버에 접속해 중지된 CodeDeploy 에이전트를 실행하고', action)
        self.assertIn('<ul class="case-flow__actions">', action)
        self.assertEqual(action.count('<li>'), 3)
        for label in ('배포 중단:', '배포 스크립트 수정:', '운영 설정 반영:'):
            self.assertIn('<strong>' + label + '</strong>', action)
        for fact in ('애플리케이션 이름과 기존 프로세스 조회 조건을 수정',
                     '*SNAPSHOT.jar에서 *.jar로 변경', 'SNAPSHOT 파일명에 의존하지 않도록',
                     'GitHub Secrets로 운영 설정 파일을 생성하는 단계를 빌드 전으로 옮기고',
                     'JWT 유효기간'):
            self.assertIn(fact, action)
        # The original script already excluded plain JARs; this was not a new change.
        self.assertNotIn('plain JAR는 제외', action)
        parser = SiteParser()
        parser.feed(case)
        links = [attrs['href'] for tag, attrs in parser.nodes if tag == 'a']
        self.assertEqual(links, ['https://github.com/potenup-dekk/DEKK-BE/blob/f20c246c353acd82a60c1619998a6a2738d22e38/appspec.yml'])
        self.assertNotIn('맡고 있었습니다', case)

    def test_auth_and_deck_separation_cases_have_independent_narratives(self):
        # These checks guard reviewed edits; they do not replace a narrative review.
        auth = self.html.split('id="dekk-member-improvement"', 1)[1].split('</article>', 1)[0]
        separation = self.html.split('id="dekk-member-deck-separation"', 1)[1].split('</article>', 1)[0]
        for case, facts, excluded in (
            (auth, ('사용자와 관리자 코드를 각각 수정',
                    '권한 정보는 구분하고, 동일하게 동작해야 하는 토큰 처리만 공통화',
                    '토큰 생성과 검증을 공통화', '인증 정책의 일관성과 유지보수성을 높였습니다',
                    'pull/182'), ('보관함', '트랜잭션', 'pull/180')),
            (separation, ('보관함 처리 방식이 바뀌면 회원 코드도 함께 검토',
                          '두 작업의 성공과 실패는 같은 트랜잭션으로 묶는 방식',
                          '이벤트 핸들러로 분리', '기존 트랜잭션에 참여',
                          '기능별 유지보수성을 높였습니다',
                          'pull/180'), ('토큰', '인증 정책', 'pull/182')),
        ):
            for fact in facts:
                self.assertIn(fact, case)
            for unrelated in (*excluded, 'Codex', '26개', '로그인 사용자 정보를 전달',
                              '9f33a9e229412b5b0e6e3ff3472356481fed2cb9'):
                self.assertNotIn(unrelated, case)
            for label in ('문제', '해결 방안 검토', '해결·개선', '성과'):
                self.assertEqual(case.count('<dt>' + label + '</dt>'), 1)
            self.assertEqual(case.count('class="project__evidence"'), 1)
            self.assertEqual(case.count('<li><a '), 1)

    def test_review_case_does_not_mix_in_lecture_title_feature(self):
        case = self.html.split('id="learnflow-review-query"', 1)[1].split('</article>', 1)[0]
        for unrelated in ('강의 제목', '내가 작성한 리뷰', 'getMyReviews'):
            self.assertNotIn(unrelated, case)
        for relevant in ('리뷰마다 회원 정보를 따로 조회', '작성자 ID를 모아 중복을 제거',
                         '회원 정보를 일괄 조회', '리뷰 목록 조회의 DB 접근 비용을 줄였습니다'):
            self.assertIn(relevant, case)

    def test_emotion_case_focuses_on_omitted_scores_not_a_screen_mismatch(self):
        case = self.html.split('id="vench-emotion-report"', 1)[1].split('</article>', 1)[0]
        outcome = case.split('<dt>성과</dt><dd>', 1)[1].split('</dd>', 1)[0]
        self.assertIn('대표 감정 외의 점수도 집계', outcome)
        self.assertIn('여러 감정의 분포를 파악하도록 개선', outcome)
        self.assertNotIn('기준을 일치시켰습니다', outcome)

    def test_outcomes_match_approved_benefit_statements(self):
        # Copy regression only; code evidence and narrative still need human review.
        expected = {
            'dekk-member-improvement': '공통 토큰 정책을 한곳에서 수정하도록 통합해, 인증 정책의 일관성과 유지보수성을 높였습니다.',
            'dekk-member-deck-separation': '보관함 처리 변경 시 회원 코드를 함께 수정해야 하는 의존성을 줄여, 기능별 유지보수성을 높였습니다.',
            'dekk-concurrent-save': '동시 요청에 따른 중복 저장과 용량 초과를 제어해, 공동 보관함 데이터의 정합성을 높였습니다.',
            'dekk-query-improvement': '화면에 쓰지 않는 카드 데이터 전송과 서버 정렬을 제거해, 보관함 목록 조회의 처리 효율을 높였습니다.',
            'learnflow-ai-outbox': 'AI 분석과 승인을 분리해 관리자의 승인 대기 부담을 줄이고, 승인과 분석 작업을 함께 저장해 작업 연결의 안정성을 높였습니다.',
            'learnflow-review-query': '리뷰마다 반복하던 작성자 DB 조회를 일괄 처리해, 리뷰 목록 조회의 DB 접근 비용을 줄였습니다.',
            'learnflow-deployment-improvement': '중복 실행을 제거하고 백업을 최신 3개로 관리해, 배포 절차를 단순화하고 백업 파일 관리 부담을 줄였습니다.',
            'vench-ai-progress': '처리 단계 안내로 사용자의 진행 상황 파악을 돕고, 본문 생성 실패 시에도 인식한 원문을 제공해 기록을 다시 작성해야 하는 부담을 줄였습니다.',
            'vench-emotion-report': '대표 감정 외의 점수도 집계해, 사용자가 기록에 함께 나타난 여러 감정의 분포를 파악하도록 개선했습니다.',
            'dekk-deployment-collaboration': '배포 지연을 해소해 팀원들이 개발한 기능을 서버에서 함께 확인하고, 각자 맡은 기능 개발과 연동 작업에 집중할 수 있는 기반을 마련했습니다.',
            'vench-audio-input': '음성 인식 전에 녹음 파일의 음량 편차를 줄였습니다.',
        }
        for case_id, text in expected.items():
            with self.subTest(case=case_id):
                case = self.html.split('id="' + case_id + '"', 1)[1].split('</article>', 1)[0]
                outcome = case.split('<dt>성과</dt><dd>', 1)[1].split('</dd>', 1)[0]
                self.assertEqual(outcome, text)

    def test_each_case_links_to_specific_public_evidence(self):
        cases = [attrs['id'] for tag, attrs in self.nodes if tag == 'article'
                 and 'project__case' in attrs.get('class', '').split()]
        self.assertEqual(len(cases), 11)
        for case_id in cases:
            content = self.html.split('id="' + case_id + '"', 1)[1].split('</article>', 1)[0]
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
        dialogs = [attrs for tag, attrs in self.nodes if tag == 'dialog'
                   and attrs.get('id') == 'project-case-dialog']
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
            self.assertIn('문제 해결과 성과 보기', trigger['aria-label'])
        cases = [attrs for tag, attrs in self.nodes if 'data-case-label' in attrs]
        self.assertEqual([attrs['data-case-label'] for attrs in cases],
                         ['인증 공통화', '회원·보관함 분리', '동시 저장', '조회 개선', '배포 협업',
                          'AI 작업 연결', '리뷰 조회', '배포 개선',
                          '진행 및 실패 대응', '음성 입력', '감정 통계'])
        self.assertTrue(all(attrs.get('id') in ids for attrs in cases))
        # Original details and source content remain present if enhancement fails to load.
        self.assertEqual(self.html.count('<details class="project__detail">'), 3)
        self.assertIn('<script src="src/project-dialog.js?v=20261007-header-bottom" defer></script>', self.html)

    def test_expanded_project_cases_have_distinct_topics_and_boundaries(self):
        learnflow = self.html.split('<li id="project-learnflow"', 1)[1].split('<li id="project-vench"', 1)[0]
        vench = self.html.split('<li id="project-vench"', 1)[1].split('<details class="project__detail">', 1)[1].split('</details>', 1)[0]
        for project in (learnflow, vench):
            parser = SiteParser()
            parser.feed(project)
            self.assertEqual(sum(tag == 'article' and 'project__case'
                                 in attrs.get('class', '').split()
                                 for tag, attrs in parser.nodes), 3)
        for case_id in ('learnflow-review-query', 'learnflow-deployment-improvement',
                        'vench-audio-input', 'vench-emotion-report'):
            self.assertIn('id="' + case_id + '"', self.html)
        self.assertNotIn('후속 heartbeat·workerId 고도화는 팀 구현', learnflow)
        self.assertIn('최신 3개만', learnflow)
        audio = vench.split('id="vench-audio-input"', 1)[1].split('</article>', 1)[0]
        self.assertIn('음량 정규화를 추가', audio)
        self.assertNotIn('정확도 향상', audio)
        self.assertNotIn('%', audio)
        progress = vench.split('id="vench-ai-progress"', 1)[1].split('</article>', 1)[0]
        self.assertNotIn('프로세스 재시작 후 자동 복구까지 보장하는 구조는 아닙니다', progress)
        self.assertNotIn('project__note', progress)
        self.assertIn('BackgroundTasks로 AI 처리를 이어갔습니다.', progress)
        css = (ROOT / 'css/style.css').read_text()
        self.assertIn('repeat(var(--case-count, 4), minmax(0, 9rem))', css)

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
        self.assertIn('<div class="case-dialog__meta"><h2 id="case-dialog-project"', self.html)
        self.assertNotIn('case-dialog-title', self.html)
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
        meta_rule = css.split('.case-dialog__meta {', 1)[1].split('}', 1)[0]
        self.assertIn('align-items: flex-end;', meta_rule)
        self.assertNotIn('--project-ink-overhang', css)
        self.assertNotIn('projectMeta.dataset.project', script)
        self.assertIn('transform: translateY(2px);', link_rule)
        for affordance in ('height: 20px;', 'line-height: 1;', 'border: 1px solid', 'background: transparent;', 'font-size: .75rem;', 'font-weight: 500;'):
            self.assertIn(affordance, link_rule)
        project_rule = css.split('.case-dialog__project {', 1)[1].split('}', 1)[0]
        self.assertIn('font-size: 1.5rem;', project_rule)
        self.assertIn('font-weight: 700;', project_rule)
        for alignment in ('display: block;', 'line-height: 1;', 'text-box-trim: trim-end;', 'text-box-edge: cap alphabetic;'):
            self.assertIn(alignment, project_rule)
        self.assertNotIn('min-height:', project_rule)
        self.assertNotIn('min-height:', link_rule)
        mobile = css.split('@media (max-width: 600px)', 1)[1]
        self.assertNotIn('.case-dialog__project { font-size:', mobile)

    def test_evidence_stays_below_cases_with_larger_text_and_icon_only_close(self):
        script = (ROOT / 'src/project-dialog.js').read_text()
        self.assertNotIn('project__case-header', script)
        close = self.html.split('<button class="case-dialog__close"', 1)[1].split('</button>', 1)[0]
        self.assertIn('aria-label="프로젝트 상세 닫기"', close)
        self.assertIn('<svg ', close)
        self.assertIn('aria-hidden="true"', close)
        self.assertNotIn('>닫기', close)
        css = (ROOT / 'css/style.css').read_text()
        close_rule = css.split('.case-dialog__close {', 1)[1].split('}', 1)[0]
        for value in ('width: 44px;', 'height: 44px;', 'border: 0;'):
            self.assertIn(value, close_rule)
        link_rule = css.split('.case-dialog .project__evidence a {', 1)[1].split('}', 1)[0]
        for value in ('font-size: 1.125rem;', 'font-weight: 600;', 'min-height: 44px;'):
            self.assertIn(value, link_rule)
        evidence_rule = css.split('.case-dialog .project__evidence {', 1)[1].split('}', 1)[0]
        self.assertIn('margin-top: 1.25rem;', evidence_rule)
        self.assertIn('padding-left: 1rem;', evidence_rule)
        self.assertIn('border-left: 2px solid transparent;', evidence_rule)
        note_rule = css.split('.case-dialog .project__note {', 1)[1].split('}', 1)[0]
        self.assertIn('padding-left: 1rem;', note_rule)
        self.assertIn('border-left: 2px solid transparent;', note_rule)

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
