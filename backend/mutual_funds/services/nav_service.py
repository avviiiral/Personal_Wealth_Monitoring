from mutual_funds.models import MutualFundNAV


class MutualFundNAVService:

    @staticmethod
    def get_nav_for_date(
        scheme,
        target_date,
    ):
        """
        Return the latest available NAV on or before
        the requested date.

        Returns:
            MutualFundNAV instance

        Raises:
            ValueError if no NAV is available.
        """

        nav = (
            MutualFundNAV.objects
            .filter(
                scheme=scheme,
                date__lte=target_date,
            )
            .order_by("-date")
            .first()
        )

        if not nav:
            raise ValueError(
                f"No NAV available for "
                f"{scheme.scheme_name} "
                f"on or before {target_date}."
            )

        if nav.nav <= 0:
            raise ValueError(
                f"Invalid NAV {nav.nav} "
                f"for {scheme.scheme_name} "
                f"on {nav.date}."
            )

        return nav