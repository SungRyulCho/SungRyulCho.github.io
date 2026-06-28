"use strict";

const categories = document.querySelector(".categories");
const projects = document.querySelectorAll(".project");
const projectsContainer = document.querySelector(".projects");

if (categories && projectsContainer) {
  categories.addEventListener("click", (event) => {
    const target = event.target.closest("[data-category]");
    const filter = target?.dataset.category;
    if (!filter) return;

    handleActiveSelection(target);
    filterProjects(filter);
  });
}

function handleActiveSelection(target) {
  const active = document.querySelector(".category--selected");
  active?.classList.remove("category--selected");
  target.classList.add("category--selected");
}

function filterProjects(filter) {
  projects.forEach((project) => {
    project.style.display =
      filter === "all" || filter === project.dataset.type ? "block" : "none";
  });
  projectsContainer.classList.add("anim-out");
  setTimeout(() => {
    projectsContainer.classList.remove("anim-out");
  }, 180);
}
