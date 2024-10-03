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

  class ButtonCloseDialog extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      const callComponentMethodOjDialogCloseResult = await Actions.callComponentMethod(context, {
        selector: '#oj-dialog',
        method: 'close',
      });
    }
  }

  return ButtonCloseDialog;
});
