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

  class ButtonCloseConfigurationDialog extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      const callComponentMethodOjDialogConfigurationCloseResult = await Actions.callComponentMethod(context, {
        selector: '#oj-dialog--configuration',
        method: 'close',
      });
    }
  }

  return ButtonCloseConfigurationDialog;
});
