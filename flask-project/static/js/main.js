document.addEventListener('DOMContentLoaded', () => {
    const body = document.body;
    const closingTimers = new WeakMap();

    const profileMenu = document.querySelector('.profile-menu');
    if (profileMenu) {
        const trigger = profileMenu.querySelector('[data-menu-toggle]');
        trigger?.addEventListener('click', (event) => {
            event.stopPropagation();
            profileMenu.classList.toggle('open');
        });
        document.addEventListener('click', (event) => {
            if (!profileMenu.contains(event.target)) {
                profileMenu.classList.remove('open');
            }
        });
    }

    document.querySelectorAll('[data-close-flash]').forEach((button) => {
        button.addEventListener('click', (event) => {
            const flash = event.currentTarget.closest('.flash');
            if (!flash) return;
            flash.classList.add('closing');
            setTimeout(() => flash.remove(), 180);
        });
    });

    const modals = new Map();
    document.querySelectorAll('.modal').forEach((modal) => {
        modals.set(modal.id, modal);
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                closeModal(modal);
            }
        });
    });

    function openModal(modal) {
        if (closingTimers.has(modal)) {
            clearTimeout(closingTimers.get(modal));
            closingTimers.delete(modal);
        }
        modal.removeAttribute('hidden');
        requestAnimationFrame(() => {
            modal.classList.add('show');
        });
        body.style.overflow = 'hidden';
    }

    function closeModal(modal) {
        modal.classList.remove('show');
        const timer = setTimeout(() => {
            modal.setAttribute('hidden', 'true');
            closingTimers.delete(modal);
        }, 220);
        closingTimers.set(modal, timer);
        body.style.overflow = '';
    }

    function addFlashMessage(category, message) {
        if (!message) return;
        const container = document.querySelector('.flash-container');
        if (!container) return;
        const flash = document.createElement('div');
        flash.className = `flash flash-${category}`;
        const span = document.createElement('span');
        span.textContent = message;
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'flash-close';
        closeBtn.setAttribute('aria-label', 'Close');
        closeBtn.dataset.closeFlash = '';
        closeBtn.innerHTML = '&times;';
        flash.append(span, closeBtn);
        container.appendChild(flash);
        closeBtn.addEventListener('click', () => {
            flash.classList.add('closing');
            setTimeout(() => flash.remove(), 180);
        });
    }

    function adjustNumericValue(target, delta) {
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        if (!element) return;
        const current = Number(element.textContent.trim());
        if (Number.isNaN(current)) return;
        element.textContent = String(current + delta);
    }

    function updateDashboardProjectStats() {
        adjustNumericValue('[data-project-count]', 1);
        adjustNumericValue('[data-stat="projects"]', 1);
        adjustNumericValue('[data-stat="owned"]', 1);
    }

    function insertProjectCard(project) {
        const list = document.querySelector('[data-project-list]');
        if (!list || !project) return;
        const empty = list.querySelector('[data-project-empty]');
        if (empty) {
            empty.remove();
        }

        const card = document.createElement('article');
        card.className = 'project-card';
        if (project.id != null) {
            card.dataset.projectId = String(project.id);
        }
        const role = project.role === 'member' ? 'member' : 'owner';
        card.dataset.role = role;

        const title = document.createElement('div');
        title.className = 'project-title';

        const heading = document.createElement('h3');
        heading.textContent = project.name || 'New Project';
        const roleChip = document.createElement('span');
        roleChip.className = `role-chip ${role}`;
        roleChip.textContent = role === 'owner' ? 'Owner' : 'Member';
        title.append(heading, roleChip);

        const summary = document.createElement('p');
        summary.className = 'project-summary';
        summary.textContent = project.description || 'Plan your tasks and collaborate effortlessly.';

        const meta = document.createElement('div');
        meta.className = 'project-meta';

        const track = document.createElement('div');
        track.className = 'progress-track';
        const bar = document.createElement('div');
        bar.className = 'progress-bar';
        const tasksTotal = Number(project.tasks_total) || 0;
        const tasksDone = Number(project.tasks_done) || 0;
        const progress = tasksTotal > 0 ? Math.round((tasksDone / tasksTotal) * 100) : 0;
        bar.style.width = `${progress}%`;
        track.appendChild(bar);

        const label = document.createElement('span');
        label.className = 'progress-label';
        if (tasksTotal > 0) {
            label.textContent = `${tasksDone} / ${tasksTotal} tasks`;
        } else {
            label.textContent = 'No tasks yet';
        }
        meta.append(track, label);

        const actions = document.createElement('div');
        actions.className = 'project-actions';
        const viewLink = document.createElement('a');
        viewLink.className = 'btn btn-outline';
        viewLink.href = project.detail_url || '#';
        viewLink.textContent = 'View';
        actions.appendChild(viewLink);

        card.append(title, summary, meta, actions);
        list.prepend(card);
    }

    function submitProjectForm(form, modal) {
        if (!form) return;
        const submitButton = form.querySelector('[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
        }
        const formData = new FormData(form);
        const method = (form.method || 'POST').toUpperCase();
        fetch(form.action, {
            method,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                Accept: 'application/json',
            },
            body: formData,
        })
            .then((response) =>
                response
                    .json()
                    .then((data) => ({ ok: response.ok, data }))
                    .catch(() => ({ ok: response.ok, data: null }))
            )
            .then(({ ok, data }) => {
                if (ok && data?.success) {
                    insertProjectCard(data.project);
                    updateDashboardProjectStats();
                    addFlashMessage('success', data.message || 'Project created successfully.');
                    form.reset();
                    if (modal) {
                        closeModal(modal);
                    }
                } else {
                    const errors = data?.errors || {};
                    let message = data?.message || 'Unable to create project.';
                    const firstKey = Object.keys(errors)[0];
                    if (firstKey && Array.isArray(errors[firstKey]) && errors[firstKey].length) {
                        message = errors[firstKey][0];
                    }
                    addFlashMessage('danger', message);
                }
            })
            .catch(() => {
                addFlashMessage('danger', 'Unexpected error creating project.');
            })
            .finally(() => {
                if (submitButton) {
                    submitButton.disabled = false;
                }
            });
    }

    document.querySelectorAll('[data-modal-open]').forEach((trigger) => {
        trigger.addEventListener('click', () => {
            const targetId = trigger.getAttribute('data-modal-open');
            const modal = modals.get(targetId);
            if (!modal) return;
            if (targetId === 'task-modal') {
                prepareTaskForm(modal, trigger.getAttribute('data-mode') === 'create', trigger.dataset);
            }
            openModal(modal);
        });
    });

    document.querySelectorAll('[data-modal-close]').forEach((button) => {
        button.addEventListener('click', () => {
            const modal = button.closest('.modal');
            if (modal) closeModal(modal);
        });
    });

    const projectModal = modals.get('project-modal');
    if (projectModal) {
        const projectForm = projectModal.querySelector('[data-project-form]');
        if (projectForm) {
            projectForm.addEventListener('submit', (event) => {
                event.preventDefault();
                submitProjectForm(projectForm, projectModal);
            });
        }
    }

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            modals.forEach((modal) => {
                if (!modal.hasAttribute('hidden')) {
                    closeModal(modal);
                }
            });
        }
    });

    const taskModal = document.getElementById('task-modal');
    let taskForm;
    let titleTarget;
    let createTitle = '';
    let editTitle = '';
    let assigneeSelect;

    if (taskModal) {
        taskForm = taskModal.querySelector('[data-task-form]');
        titleTarget = taskModal.querySelector('[data-task-modal-title]');
        const dialog = taskModal.querySelector('.modal-dialog');
        createTitle = dialog?.dataset.titleCreate || 'New Task';
        editTitle = dialog?.dataset.titleEdit || 'Edit Task';
        assigneeSelect = taskModal.querySelector('select[name="assignee_id"]');

        document.querySelectorAll('[data-edit-task]').forEach((button) => {
            button.addEventListener('click', () => {
                const modal = modals.get('task-modal');
                if (!modal) return;
                prepareTaskForm(modal, false, button.dataset);
                openModal(modal);
            });
        });
    }

    function selectAssigneeOption(value) {
        if (!assigneeSelect) return;
        const normalized = value == null ? '' : String(value);
        const options = Array.from(assigneeSelect.options);
        const match = options.find((option) => option.value === normalized);
        if (match) {
            assigneeSelect.value = normalized;
        } else if (options.length) {
            assigneeSelect.value = options[0].value;
        }
    }

    function prepareTaskForm(modal, isCreate, dataset = {}) {
        if (!taskForm || !titleTarget) return;
        taskForm.reset();
        const createAction = taskForm.dataset.createAction;
        const updateTemplate = taskForm.dataset.updateTemplate;
        const titleField = taskForm.querySelector('[name="title"]');
        const descriptionField = taskForm.querySelector('[name="description"]');
        const statusField = taskForm.querySelector('[name="status"]');
        const dueField = taskForm.querySelector('[name="due_date"]');

        if (isCreate) {
            if (createAction) taskForm.action = createAction;
            titleTarget.textContent = createTitle;
            taskForm.dataset.mode = 'create';
            selectAssigneeOption(assigneeSelect?.options?.[0]?.value ?? '0');
            return;
        }

        const id = dataset.id;
        if (!id) return;
        titleTarget.textContent = editTitle;
        taskForm.dataset.mode = 'edit';
        if (updateTemplate) {
            taskForm.action = updateTemplate.replace(/0$/, id);
        }

        if (titleField) titleField.value = dataset.title || '';
        if (descriptionField) descriptionField.value = dataset.description || '';
        if (statusField) statusField.value = dataset.status || statusField.value;
        if (dueField) dueField.value = dataset.due || '';
        const assigneeValue = dataset.assignee ?? assigneeSelect?.options[0]?.value ?? '0';
        selectAssigneeOption(assigneeValue);
    }
    const STATUS_LABELS = {
        todo: 'To do',
        in_progress: 'In progress',
        done: 'Completed',
    };

    function refreshTaskBoardStats() {
        const projectSection = document.querySelector('[data-project-page]');
        if (!projectSection) return;

        const columns = projectSection.querySelectorAll('.task-column');
        let total = 0;
        let done = 0;

        columns.forEach((column) => {
            const status = column.dataset.status;
            const tasks = column.querySelectorAll('.task-card');
            const count = tasks.length;
            total += count;
            if (status === 'done') {
                done += count;
            }
            const badge = column.querySelector('[data-column-count]');
            if (badge) {
                badge.textContent = String(count);
            }
        });

        const active = total - done;

        const totalEl = projectSection.querySelector('[data-project-stat="total"]');
        if (totalEl) {
            totalEl.textContent = String(total);
        }
        const doneEl = projectSection.querySelector('[data-project-stat="done"]');
        if (doneEl) {
            doneEl.textContent = String(done);
        }
        const activeEl = projectSection.querySelector('[data-project-stat="active"]');
        if (activeEl) {
            activeEl.textContent = String(active);
        }

        const progressBar = projectSection.querySelector('[data-project-progress]');
        if (progressBar) {
            const percent = total > 0 ? Math.round((done / total) * 100) : 0;
            progressBar.style.width = `${percent}%`;
        }

        const statusChip = projectSection.querySelector('[data-project-status]');
        if (statusChip) {
            statusChip.classList.remove('success', 'warning', 'neutral');
            if (total === 0) {
                statusChip.classList.add('neutral');
                statusChip.textContent = 'No tasks';
            } else if (done === total) {
                statusChip.classList.add('success');
                statusChip.textContent = STATUS_LABELS.done || 'Completed';
            } else {
                statusChip.classList.add('warning');
                statusChip.textContent = STATUS_LABELS.in_progress || 'In progress';
            }
        }
    }

    const projectSection = document.querySelector('[data-project-page]');
    if (projectSection) {
        const projectId = projectSection.dataset.projectId;
        const csrfToken = projectSection.dataset.csrf;
        const board = projectSection.querySelector('[data-task-board]');
        if (projectId && board) {
            const cards = board.querySelectorAll('.task-card');
            cards.forEach((card) => wireCard(card));

            const columns = board.querySelectorAll('.task-column');
            columns.forEach((column) => wireColumn(column));

            refreshTaskBoardStats();
        }

        function wireCard(card) {
            card.addEventListener('dragstart', (event) => {
                event.dataTransfer.setData('text/plain', card.dataset.taskId || '');
                event.dataTransfer.effectAllowed = 'move';
                card.classList.add('dragging');
                const originColumn = card.closest('.task-column');
                card.dataset.originStatus = card.dataset.status || originColumn?.dataset.status || '';
                card.dataset.originIndex = String(
                    Array.from(card.parentElement?.children || []).indexOf(card)
                );
            });
            card.addEventListener('dragend', () => {
                card.classList.remove('dragging');
            });
        }

        function wireColumn(column) {
            const tasksContainer = getTasksContainer(column);
            column.addEventListener('dragover', (event) => {
                event.preventDefault();
                event.dataTransfer.dropEffect = 'move';
                column.classList.add('drop-ready');
                const dragging = board.querySelector('.task-card.dragging');
                if (!dragging) return;
                const afterElement = getDragAfterElement(tasksContainer, event.clientY);
                if (afterElement == null) {
                    tasksContainer.appendChild(dragging);
                } else {
                    tasksContainer.insertBefore(dragging, afterElement);
                }
            });
            column.addEventListener('dragleave', () => {
                column.classList.remove('drop-ready');
            });
            column.addEventListener('drop', (event) => {
                event.preventDefault();
                column.classList.remove('drop-ready');
                const taskId = event.dataTransfer.getData('text/plain');
                if (!taskId) return;
                const newStatus = column.dataset.status;
                if (!newStatus) return;
                const card = board.querySelector(`[data-task-id="${taskId}"]`);
                if (!card || card.dataset.status === newStatus) return;
                const previousStatus = card.dataset.status || card.dataset.originStatus || '';
                const previousIndex = card.dataset.originIndex;
                card.dataset.status = newStatus;
                refreshTaskBoardStats();
                updateTaskStatus(projectId, taskId, newStatus, csrfToken)
                    .then(() => {
                        card.dataset.originStatus = newStatus;
                        card.dataset.originIndex = String(
                            Array.from(card.parentElement?.children || []).indexOf(card)
                        );
                        const chip = card.querySelector('.chip.subtle');
                        if (chip) {
                            chip.textContent = STATUS_LABELS[newStatus] || newStatus;
                        }
                        const editTrigger = card.querySelector('[data-edit-task]');
                        if (editTrigger) {
                            editTrigger.dataset.status = newStatus;
                        }
                        refreshTaskBoardStats();
                    })
                    .catch(() => {
                        card.dataset.status = previousStatus;
                        const originColumn = board.querySelector(
                            `.task-column[data-status="${card.dataset.originStatus}"]`
                        );
                        const originContainer = getTasksContainer(originColumn);
                        if (originContainer) {
                            const children = Array.from(originContainer.children);
                            const index = Number(previousIndex);
                            if (Number.isInteger(index) && index >= 0 && index < children.length) {
                                originContainer.insertBefore(card, children[index]);
                            } else {
                                originContainer.appendChild(card);
                            }
                        }
                        refreshTaskBoardStats();
                    });
            });
        }

        function getTasksContainer(column) {
            return column?.querySelector('.tasks') || column;
        }

        function getDragAfterElement(container, y) {
            const elements = [...container.querySelectorAll('.task-card:not(.dragging)')];
            return elements.reduce(
                (closest, child) => {
                    const box = child.getBoundingClientRect();
                    const offset = y - box.top - box.height / 2;
                    if (offset < 0 && offset > closest.offset) {
                        return { offset, element: child };
                    }
                    return closest;
                },
                { offset: Number.NEGATIVE_INFINITY, element: null }
            ).element;
        }
    }

    function updateTaskStatus(projectId, taskId, status, csrfToken) {
        return fetch(`/projects/${projectId}/tasks/${taskId}/move`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken || '',
            },
            body: JSON.stringify({ status }),
        }).then((response) => {
            if (!response.ok) {
                throw new Error('Failed to update task status');
            }
            return response.json();
        });
    }
});
