from warehouse.login import login

urls = [
    ("/login", (login.PageMaker, "HandleLogin"), "POST"),
    ("/login", (login.PageMaker, "RequestLogin")),
    ("/logout", (login.PageMaker, "RequestLogout")),
    ("/usersettings", (login.PageMaker, "RequestUserSettings")),
    ("/apisettings", (login.PageMaker, "RequestApiSettings")),
    ("/resetpassword", (login.PageMaker, "RequestResetPassword")),
    ("/resetpassword/([^/]*)/(.*)", (login.PageMaker, "RequestResetPassword")),
]
