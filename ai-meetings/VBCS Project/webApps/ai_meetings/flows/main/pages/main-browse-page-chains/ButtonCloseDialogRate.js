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

  class ButtonCloseDialogRate extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      const callComponentMethodOjDialogRateCloseResult = await Actions.callComponentMethod(context, {
        selector: '#oj-dialog--rate',
        method: 'close',
      });
    }
  }

  return ButtonCloseDialogRate;
});
