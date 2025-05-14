define([
  'vb/action/actionChain',
  'vb/action/actions',
  'vb/action/actionUtils',
], (
  ActionChain,
  Actions,
  ActionUtils
) => {
  'use strict';

  class openAvatarMenu extends ActionChain {

    /**
     * Opens the menu invoked from avatar icon in the header
     * @param {Object} context
     */
    async run(context) {
      const { $application } = context;

      const callHeaderAvatarMenuOpenResult = await Actions.callComponentMethod(context, {
        selector: '#header-avatar-menu',
        method: 'open',
        params: [
          '#header-avatar'
        ],
      });
    }
  }

  return openAvatarMenu;
});
