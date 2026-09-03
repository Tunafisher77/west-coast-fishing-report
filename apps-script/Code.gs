/**
 * Secure mail gateway for the West Coast Fishing Report.
 *
 * Required Script Properties:
 *   FISHING_WEBHOOK_TOKEN - long random secret shared with GitHub
 *   FISHING_REPORT_TO     - destination email address
 */
function initializeFishingReportMailer() {
  var properties = PropertiesService.getScriptProperties();
  var email = Session.getEffectiveUser().getEmail();
  if (!email) {
    throw new Error('Google did not return your email. Set FISHING_REPORT_TO manually in Script Properties.');
  }

  var token = Utilities.getUuid().replace(/-/g, '') +
              Utilities.getUuid().replace(/-/g, '');
  properties.setProperties({
    FISHING_WEBHOOK_TOKEN: token,
    FISHING_REPORT_TO: email
  });

  console.log('Destination email: ' + email);
  console.log('GitHub FISHING_WEBHOOK_TOKEN (copy now): ' + token);
}

function doPost(e) {
  try {
    var properties = PropertiesService.getScriptProperties();
    var expectedToken = properties.getProperty('FISHING_WEBHOOK_TOKEN');
    var reportTo = properties.getProperty('FISHING_REPORT_TO');

    if (!expectedToken || !reportTo) {
      return jsonResponse_({ok: false, error: 'Mailer is not configured'});
    }

    var payload = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    if (!payload.token || payload.token !== expectedToken) {
      return jsonResponse_({ok: false, error: 'Unauthorized'});
    }
    if (!payload.subject || !payload.html) {
      return jsonResponse_({ok: false, error: 'subject and html are required'});
    }
    if (payload.html.length > 1500000) {
      return jsonResponse_({ok: false, error: 'Report is too large'});
    }

    MailApp.sendEmail({
      to: reportTo,
      subject: String(payload.subject).slice(0, 200),
      body: 'This fishing report requires an HTML-capable email client.',
      htmlBody: payload.html,
      name: 'West Coast Fishing Report'
    });

    return jsonResponse_({
      ok: true,
      remainingDailyQuota: MailApp.getRemainingDailyQuota()
    });
  } catch (error) {
    console.error(error);
    return jsonResponse_({ok: false, error: String(error)});
  }
}

function doGet() {
  return jsonResponse_({ok: true, service: 'West Coast Fishing Report mail gateway'});
}

function testFishingReportEmail() {
  var reportTo = PropertiesService.getScriptProperties().getProperty('FISHING_REPORT_TO');
  if (!reportTo) throw new Error('Set FISHING_REPORT_TO in Script Properties first.');
  MailApp.sendEmail({
    to: reportTo,
    subject: '[TEST] West Coast Fishing Report Mailer',
    body: 'The Google Apps Script mail gateway is configured correctly.',
    htmlBody: '<h2>Mailer connected</h2><p>The West Coast Fishing Report can now send HTML email.</p>',
    name: 'West Coast Fishing Report'
  });
}

function jsonResponse_(value) {
  return ContentService
    .createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}
