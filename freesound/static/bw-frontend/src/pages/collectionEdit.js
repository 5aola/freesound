import { prepareAddMaintainersModalAndFields } from '../components/collectionsModal';
import { initEditableSoundGrid } from '../utils/editableSoundGrid';

prepareAddMaintainersModalAndFields(document);
document.querySelectorAll('[data-editable-sound-grid]').forEach(initEditableSoundGrid);
