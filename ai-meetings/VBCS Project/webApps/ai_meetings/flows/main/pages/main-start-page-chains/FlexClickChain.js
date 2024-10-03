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

  class FlexClickChain extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      const callComponentMethodOjDialogOpenResult = await Actions.callComponentMethod(context, {
        selector: '#oj-dialog',
        method: 'open',
      });
    }
  }

  return FlexClickChain;
});
