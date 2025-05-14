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

  class CopyTranscription extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;


        
            navigator.clipboard.writeText($page.variables.transcriptionText).then(() => {
                    Actions.fireNotificationEvent(context, {
                    summary: 'Now you have the transcription in your clipboard',
                    type: 'info',
                    displayMode: 'transient',
                  });
            }).catch(err => {
                console.error('Failed to copy text: ', err);
            });

   
    }
  }

  return CopyTranscription;
});
