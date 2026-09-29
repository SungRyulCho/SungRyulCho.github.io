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

    def test_education_course_and_org_labels_are_consistent(self):
        items = self.html.split('<article class="education-item">')[1:]
        self.assertEqual(len(items), 2)
        for item in items:
            content = item.split('</article>', 1)[0]
            self.assertEqual(content.count('<p>교육 과정:'), 1)
            self.assertEqual(content.count('<p class="education-item__org">기관:'), 1)

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
        self.assertEqual(len(cases), 4)
        for case in cases:
            content = case.split('</dl>', 1)[0]
            self.assertEqual(content.count('<dt>'), 3)
            self.assertLess(content.index('<dt>문제</dt>'), content.index('<dt>해결 방안 검토</dt>'))
            self.assertLess(content.index('<dt>해결 방안 검토</dt>'), content.index('<dt>해결·개선</dt>'))

    def test_backend_project_mapping_and_clear_responsibilities(self):
        backend = self.html.split('id="backend-skills-title"', 1)[1].split('</section>', 1)[0]
        self.assertIn('DEKK·LearnFlow는 Java/Spring Boot로', backend)
        self.assertIn('Vench AI는 Python/FastAPI로', backend)
        for tasks in self.html.split('<ul class="project__tasks">')[1:]:
            items = tasks.split('</ul>', 1)[0].split('<li>')[1:]
            self.assertEqual(len(items), 4)
            for item in items:
                text = item.split('</li>', 1)[0]
                self.assertTrue(text.endswith(('구현', '구성', '개선')), text)

    def test_responsibilities_explain_features_before_technical_details(self):
        self.assertIn('패션 카드를 컬렉션(덱)에 모으고', self.html)
        for tasks in self.html.split('<ul class="project__tasks">')[1:]:
            content = tasks.split('</ul>', 1)[0]
            self.assertEqual(content.count('<strong>'), 4)
            self.assertEqual(content.count(':</strong>'), 4)
            for implementation_term in ('Outbox', '작업 선점', '분산 락', '메트릭', '토큰 재발급'):
                self.assertNotIn(implementation_term, content)
        for retained_detail in ('Redisson 분산 락', 'ai_outbox', 'GROUP BY와 ROW_NUMBER', 'BackgroundTasks'):
            self.assertIn(retained_detail, self.html)

    def test_model_names_not_listed_as_technology_stacks(self):
        for marker in ('<p class="skill-card__tools">', '<p class="project__stack">'):
            for block in self.html.split(marker)[1:]:
                stack = block.split('</p>', 1)[0]
                self.assertNotIn('EXAONE', stack)
                self.assertNotIn('mDeBERTa', stack)
        self.assertIn('Faster-Whisper · Transformers · llama.cpp', self.html)

    def test_about_infrastructure_uses_technologies_not_ai_features(self):
        about = self.html.split('<section id="about"', 1)[1].split('</section>', 1)[0]
        self.assertNotIn('AI &amp; Operations', about)
        self.assertNotIn('음성 인식 · 로컬 LLM · 비동기 처리', about)
        self.assertIn('Infrastructure</h3>', about)
        self.assertIn('AWS · GCP · Docker Compose', about)

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
