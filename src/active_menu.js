"use strict";

const sectionIds = ["#home", "#about", "#skills", "#work", "#evidence", "#contact"];
const sections = sectionIds
  .map((id) => document.querySelector(id))
  .filter(Boolean);
const navItems = sectionIds.map((id) =>
  document.querySelector(`.header__menu__item[href="${id}"]`)
);
const visibleSections = sectionIds.map(() => false);
let activeNavItem = navItems.find(Boolean);

const observer = new IntersectionObserver(observerCallback, {
  rootMargin: "-20% 0px 0px 0px",
  threshold: [0, 0.98],
});

sections.forEach((section) => observer.observe(section));

function observerCallback(entries) {
  let selectLastOne = false;
  entries.forEach((entry) => {
    const index = sectionIds.indexOf(`#${entry.target.id}`);
    visibleSections[index] = entry.isIntersecting;
    selectLastOne =
      index === sectionIds.length - 1 &&
      entry.isIntersecting &&
      entry.intersectionRatio >= 0.95;
  });

  const navIndex = selectLastOne
    ? sectionIds.length - 1
    : findFirstIntersecting(visibleSections);
  selectNavItem(navIndex);
}

function findFirstIntersecting(intersections) {
  const index = intersections.indexOf(true);
  return index >= 0 ? index : 0;
}

function selectNavItem(index) {
  const navItem = navItems[index];
  if (!navItem || !activeNavItem) return;
  activeNavItem.classList.remove("active");
  activeNavItem = navItem;
  activeNavItem.classList.add("active");
}
