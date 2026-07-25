// Editable sound grid for the collection/pack edit pages. The only client state is the
// pending delta, held in the form's hidden [data-delta] inputs, which is also the submit
// contract. Card toggles just flip an id in its input; search/sort/pagination and modal
// adds re-fetch the grid with the delta. See utils/editable_sound_grid.py.

import { prepareAddSoundsModalDynamic } from '../components/addSoundsModal';
import { updateActionUI } from '../components/objectSelector';

export const initEditableSoundGrid = root => {
  const inputs = {}; // delta name -> hidden input
  root.closest('form').querySelectorAll('input[data-delta]').forEach(input => {
    inputs[input.dataset.delta] = input;
  });
  const searchInput = root.querySelector('[data-grid-search]');
  const sortSelect = root.querySelector('[data-grid-sort]');
  const contentEl = root.querySelector('[data-grid-content]');
  const maxFeatured = parseInt(root.dataset.maxFeatured, 10) || Infinity;
  let currentPage = 1;

  const ids = name => new Set(inputs[name].value.split(',').filter(id => id !== ''));
  const toggle = (name, id) => {
    const set = ids(name);
    if (set.has(id)) set.delete(id);
    else set.add(id);
    inputs[name].value = [...set].join(',');
  };

  // Button state and counts derive from the inputs, recompute after every toggle and swap
  const sync = () => {
    const removed = ids('removed');
    const featured = inputs.featured ? ids('featured') : new Set();
    const featuredCount = [...featured].filter(id => !removed.has(id)).length;
    const atLimit = featuredCount >= maxFeatured;

    contentEl.querySelectorAll('[data-object-id]').forEach(card => {
      const id = card.dataset.objectId;
      updateActionUI(card, 'removed', removed.has(id));
      if (inputs.featured) {
        updateActionUI(card, 'featured', featured.has(id));
        const featuredBtn = card.querySelector('[data-action="featured"]');
        featuredBtn.disabled = removed.has(id) || (!featured.has(id) && atLimit);
      }
    });

    const totalEl = contentEl.querySelector('[data-grid-total]');
    const total = totalEl ? parseInt(totalEl.dataset.gridTotal, 10) : 0;
    root.querySelector('[data-grid-count]').textContent = total - removed.size;
    const featuredCountEl = root.querySelector('[data-grid-featured-count]');
    if (featuredCountEl) featuredCountEl.textContent = featuredCount;
  };

  const refresh = () => {
    const values = { page: currentPage, q: searchInput.value.trim(), s: sortSelect.value };
    Object.values(inputs).forEach(input => {
      values[input.name] = input.value;
    });
    window.htmx.ajax('GET', window.location.pathname, {
      target: contentEl,
      swap: 'innerHTML',
      values,
    });
  };
  const refreshFromFirstPage = () => {
    currentPage = 1;
    refresh();
  };

  root.addEventListener('click', evt => {
    const actionBtn = evt.target.closest('[data-action]');
    const pageLink = evt.target.closest('a[data-page]');
    const clearSearchLink = evt.target.closest('[data-clear-search]');
    if (actionBtn) {
      evt.preventDefault();
      toggle(actionBtn.dataset.action, actionBtn.closest('[data-object-id]').dataset.objectId);
      sync();
    } else if (pageLink) {
      evt.preventDefault();
      currentPage = parseInt(pageLink.dataset.page, 10) || 1;
      refresh();
    } else if (clearSearchLink) {
      evt.preventDefault();
      searchInput.value = '';
      refreshFromFirstPage();
    }
  });

  searchInput.addEventListener('keydown', evt => {
    if (evt.key === 'Enter') {
      evt.preventDefault();
      refreshFromFirstPage();
    }
  });
  searchInput.addEventListener('search', refreshFromFirstPage);
  sortSelect.addEventListener('change', refreshFromFirstPage);
  contentEl.addEventListener('htmx:afterSwap', sync);

  // Saved members are already excluded server-side, only send pending adds
  prepareAddSoundsModalDynamic(root, () => inputs.added.value, newIds => {
    const set = ids('added');
    newIds.forEach(id => set.add(String(id)));
    inputs.added.value = [...set].join(',');
    refresh();
  });

  sync();
};
