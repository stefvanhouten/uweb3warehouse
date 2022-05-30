import uweb3
from uweb3.libs import mail

from base import basepages
from base.login import model


class PageMaker(basepages.PageMaker):
    @uweb3.decorators.checkxsrf
    @uweb3.decorators.TemplateParser("logout.html")
    def RequestLogout(self):
        """Handles logouts"""
        message = "You where already logged out."
        if self.user:
            message = ""
            if "action" in self.post:
                session = model.Session(self.connection)
                session.Delete()
                message = "Logged out."
        return {"message": message}

    @uweb3.decorators.checkxsrf
    def HandleLogin(self):
        """Handles a username/password combo post."""
        if self.user or "email" not in self.post or "password" not in self.post:
            return self.RequestIndex()
        url = (
            self.post.getfirst("url", None)
            if self.post.getfirst("url", "").startswith("/")
            else "/"
        )
        try:
            self._user = model.User.FromLogin(
                self.connection,
                self.post.getfirst("email"),
                self.post.getfirst("password"),
            )
            model.Session.Create(self.connection, int(self.user), path="/")
            print("login successful.", self.post.getfirst("email"))
            # redirect 303 to make sure we GET the next page, not post again to avoid leaking login details.
            return self.req.Redirect(url, httpcode=303)
        except uweb3.model.NotExistError as error:
            self.parser.RegisterTag("loginerror", "%s" % error)
            print("login failed.", self.post.getfirst("email"))
        return self.RequestLogin(url)

    @uweb3.decorators.checkxsrf
    def RequestResetPassword(self, email=None, resethash=None):
        """Handles the post for the reset password."""
        message = None
        error = False
        if not email and not resethash:
            try:
                user = model.User.FromEmail(
                    self.connection, self.post.getfirst("email", "")
                )
            except uweb3.model.NotExistError:
                error = True
                if self.debug:
                    print(
                        "Password reset request for unknown user %s:"
                        % self.post.getfirst("email", "")
                    )
            if not error:
                resethash = user.PasswordResetHash()
                content = self.parser.Parse(
                    "email/resetpass.txt",
                    email=user["email"],
                    host=self.options["general"]["host"],
                    resethash=resethash,
                )
                try:
                    with mail.MailSender(
                        local_hostname=self.options["general"]["host"]
                    ) as send_mail:
                        send_mail.Text(user["email"], "CMS password reset", content)
                except mail.SMTPConnectError:
                    if not self.debug:
                        return self.Error(
                            "Mail could not be send due to server error, please contact support."
                        )
                if self.debug:
                    print("Password reset for %s:" % user["email"], content)

            message = "If that was an email address that we know, a mail with reset instructions will be in your mailbox soon."
            return self.parser.Parse("reset.html", message=message)
        try:
            user = model.User.FromEmail(self.connection, email)
        except uweb3.model.NotExistError:
            return self.parser.Parse(
                "reset.html", message="Sorry, that's not the right reset code."
            )
        if resethash != user.PasswordResetHash():
            return self.parser.Parse(
                "reset.html", message="Sorry, that's not the right reset code."
            )

        if "password" in self.post:
            if self.post.getfirst("password") == self.post.getfirst(
                "password_confirm", ""
            ):
                try:
                    user.UpdatePassword(self.post.getfirst("password", ""))
                except ValueError:
                    return self.parser.Parse(
                        "reset.html",
                        message="Password too short, 8 characters minimal.",
                    )
                model.Session.Create(self.connection, int(user), path="/")
                self._user = user
                return self.parser.Parse(
                    "reset.html",
                    message="Your password has been updated, and you are logged in.",
                )
            else:
                return self.parser.Parse(
                    "reset.html", message="The passwords don't match."
                )
        return self.parser.Parse(
            "resetform.html", resethash=resethash, resetuser=user, message=""
        )

    def _ReadSession(self):
        """Attempts to read the session for this user from his session cookie"""
        try:
            user = model.Session(self.connection)
        except Exception:
            raise ValueError("Session cookie invalid")
        try:
            user = model.User.FromPrimary(self.connection, int(str(user)))
        except uweb3.model.NotExistError:
            return None
        if user["active"] != "true":
            raise ValueError("User not active, session invalid")
        return user
