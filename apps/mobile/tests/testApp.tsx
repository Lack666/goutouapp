import RootLayout from '../app/_layout';
import Home from '../app/index';
import Chat from '../app/chat';
import Relationship from '../app/relationship';
import Import from '../app/import';
import History from '../app/history';
import Settings from '../app/settings';
import NotFound from '../app/+not-found';
export const app = {
  _layout: RootLayout,
  index: Home,
  chat: Chat,
  relationship: Relationship,
  import: Import,
  history: History,
  settings: Settings,
  '+not-found': NotFound,
};
