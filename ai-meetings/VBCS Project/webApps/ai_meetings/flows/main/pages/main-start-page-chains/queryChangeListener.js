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

  class queryChangeListener extends ActionChain {

    /**
     * @param {Object} context
     * @param {Object} params
     * @param {{oldValue:string,value:string}} params.event
     */
    async run(context, { event }) {
      const { $page, $flow, $application } = context;

      if ($page.variables.query.length>1) {

        await Actions.callChain(context, {
          chain: 'ButtonActionSendChat',
        });

        await Actions.resetDirtyDataStatus(context, {
        });
      }
    }
  }

  return queryChangeListener;
});
